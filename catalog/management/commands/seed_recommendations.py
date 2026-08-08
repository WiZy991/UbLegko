"""Создаёт пары рекомендаций: фасовки, комплекты и связи с инвентарём."""

from collections import defaultdict

from django.core.management.base import BaseCommand

from catalog.models import Product, ProductRecommendation
from catalog.recommendations import (
    CHEMISTRY_CATEGORIES,
    _accessory_role,
    _is_stop_product,
    pack_family_key,
    product_role,
)


COMPLEMENTARY_NAME_PAIRS = [
    ('ALFA-GEL', 'ALFA-20'),
    ('ALFA-20', 'ALFA-GEL'),
    ('Amol', 'REM-700'),
    ('REM-700', 'Amol'),
    ('FORMULA X-5', 'FORMULA X-3'),
    ('FORMULA X-3', 'FORMULA X-5'),
    ('HEAVY DUTY', 'Amol'),
    ('LAMINOL', 'CITRIC'),
    ('G-2', 'MARIO'),
    ('MARIO', 'G-2'),
]

ACCESSORY_SORT = {'cloth': 10, 'glove': 11, 'dispenser': 12, 'bucket': 13, 'mop': 14}


def _pick_accessories(products: list[Product]) -> dict[str, Product]:
    chosen: dict[str, Product] = {}
    # Сначала товары из «Сопутствующие», с приоритетом явных названий
    ordered = sorted(
        products,
        key=lambda p: (
            0 if (p.category.name if p.category_id else '') == 'Сопутствующие товары' else 1,
            0 if 'тряпк' in (p.name or '').casefold() else 1,
            0 if 'дозатор' in (p.name or '').casefold() else 1,
            0 if 'перчатк' in (p.name or '').casefold() else 1,
            p.name,
        ),
    )
    for p in ordered:
        if _is_stop_product(p):
            continue
        role = _accessory_role(p)
        if not role or role == 'accessory_generic':
            continue
        if role not in chosen:
            chosen[role] = p
    return chosen


class Command(BaseCommand):
    help = 'Строит рекомендации: фасовки, комплекты и инвентарь (тряпки/перчатки/дозаторы)'

    def handle(self, *args, **options):
        products = list(
            Product.objects.filter(is_visible=True).select_related('category').order_by('name')
        )
        existing = {
            (r.product_id, r.recommended_product_id)
            for r in ProductRecommendation.objects.only('product_id', 'recommended_product_id')
        }
        to_create: list[ProductRecommendation] = []

        def queue(a: Product, b: Product, sort_order: int = 0) -> None:
            if a.id == b.id or _is_stop_product(a) or _is_stop_product(b):
                return
            key = (a.id, b.id)
            if key in existing:
                return
            existing.add(key)
            to_create.append(
                ProductRecommendation(
                    product=a,
                    recommended_product=b,
                    sort_order=sort_order,
                )
            )

        family_pairs = 0
        pair_links = 0
        accessory_links = 0

        # 1) Фасовки одной линейки
        families: dict[str, list[Product]] = defaultdict(list)
        for p in products:
            if _is_stop_product(p):
                continue
            key = pack_family_key(p.name)
            if len(key) < 3:
                continue
            families[key].append(p)

        for members in families.values():
            if len(members) < 2:
                continue
            for p in members:
                for other in members:
                    before = len(to_create)
                    queue(p, other, 0)
                    if len(to_create) > before:
                        family_pairs += 1

        # 2) Явные комплементарные пары химии
        for left_sub, right_sub in COMPLEMENTARY_NAME_PAIRS:
            lefts = [
                p
                for p in products
                if left_sub.casefold() in p.name.casefold() and not _is_stop_product(p)
            ]
            rights = [
                p
                for p in products
                if right_sub.casefold() in p.name.casefold() and not _is_stop_product(p)
            ]
            if not lefts or not rights:
                continue
            left = sorted(lefts, key=lambda x: (x.price, x.name))[0]
            right = sorted(rights, key=lambda x: (x.price, x.name))[0]
            if left.id == right.id:
                continue
            before = len(to_create)
            queue(left, right, 5)
            queue(right, left, 5)
            pair_links += len(to_create) - before

        # 3) Химия → инвентарь (по одной титульной фасовке на линейку)
        accessories = _pick_accessories(products)
        if accessories:
            titles: dict[str, Product] = {}
            for p in products:
                if _is_stop_product(p) or product_role(p) == 'accessory':
                    continue
                if not p.category_id or p.category.name not in CHEMISTRY_CATEGORIES:
                    continue
                fam = pack_family_key(p.name) or str(p.id)
                cur = titles.get(fam)
                if cur is None or (p.price, p.name) < (cur.price, cur.name):
                    titles[fam] = p

            # Ограничим число титульных линеек, чтобы не раздувать БД
            title_list = sorted(titles.values(), key=lambda x: x.name)[:80]
            for title in title_list:
                for role_name, acc in accessories.items():
                    order = ACCESSORY_SORT.get(role_name, 20)
                    before = len(to_create)
                    queue(title, acc, order)
                    if len(to_create) > before:
                        accessory_links += 1

            # Обратно: каждый инвентарь → несколько популярных средств уборки
            featured_chem = [
                p
                for p in products
                if p.category_id
                and p.category.name == 'Общая уборка'
                and not _is_stop_product(p)
                and product_role(p) != 'accessory'
            ][:12]
            for acc in accessories.values():
                for chem in featured_chem:
                    before = len(to_create)
                    queue(acc, chem, 20)
                    if len(to_create) > before:
                        accessory_links += 1

        if to_create:
            ProductRecommendation.objects.bulk_create(to_create, ignore_conflicts=True, batch_size=500)

        total = ProductRecommendation.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f'Готово: добавлено до {len(to_create)} '
                f'(фасовки: {family_pairs}, комплекты: {pair_links}, инвентарь: {accessory_links}), '
                f'всего в БД: {total}. '
                f'Инвентарь: {", ".join(f"{k}={v.name}" for k, v in accessories.items()) or "—"}'
            )
        )
