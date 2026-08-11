"""Рекомендации по общим номерам групп + запасной автоподбор."""

from __future__ import annotations

import operator
import re
from collections.abc import Iterable
from dataclasses import dataclass
from functools import reduce

from django.db.models import Q, QuerySet

from .models import Product

DEFAULT_LIMIT = 8

STOP_WORDS = (
    'бумага',
    'офис',
    'канц',
    'принтер',
    'картридж',
    'скоба',
    'скрепк',
    'папка',
    'тетрад',
    'салфетки бумаж',
    'бумажные неароматиз',
)

AFFINITY_GROUPS: dict[str, tuple[str, ...]] = {
    'descaler': (
        'ржавчин', 'известков', 'налёта', 'налета', 'накип', 'кальци',
        'кислот', 'citric', 'alfa-gel', 'alfa gel', 'descal',
    ),
    'degreaser': (
        'жир', 'антижир', 'зажирен', 'degreaser', 'amol', 'кухн', 'grill',
        'heavy duty', 'formula x',
    ),
    'laundry': (
        'стирк', 'белья', 'отбеливат', 'delin', 'dezet', 'ткан',
    ),
    'dishwash': (
        'посудомоеч', 'посуды', 'dish', 'кофемаш',
    ),
    'sanitizer': (
        'антисептик', 'дезинфек', 'dez', 'хлор', 'sanit',
    ),
    'auto': (
        'авто', 'кузов', 'шин', 'салон', 'bahler', 'чернитель', 'антидождь',
    ),
    'soap': (
        'мыло', 'cream soap', 'крем-мыло',
    ),
    'freshener': (
        'ароматизатор', 'освежител', 'поглотител', 'запаха', 'aroma',
    ),
}

ACCESSORY_ROLES: dict[str, tuple[str, ...]] = {
    'cloth': ('тряпк', 'салфет', 'микрофибр', 'губка', 'губки', 'wipe'),
    'glove': ('перчатк',),
    'dispenser': ('дозатор', 'распыл', 'пульвериз', 'триггер'),
    'bucket': ('ведро',),
    'mop': ('vileda', 'швабр', 'насадк', 'ultramax', 'моп'),
}

CROSS_SELL: dict[str, tuple[str, ...]] = {
    'chemistry': ('cloth', 'glove', 'dispenser', 'bucket'),
    'descaler': ('cloth', 'glove', 'dispenser', 'bucket'),
    'degreaser': ('cloth', 'glove', 'dispenser', 'bucket'),
    'freshener': ('cloth', 'dispenser'),
    'soap': ('dispenser', 'glove'),
    'sanitizer': ('dispenser', 'glove'),
    'laundry': ('glove', 'cloth'),
    'dishwash': ('glove', 'cloth'),
    'auto': ('glove', 'cloth'),
    'accessory': (),
}

CHEMISTRY_CATEGORIES = frozenset({
    'Общая уборка',
    'Химчистка',
    'Для стирки',
    'Для посудомоечных машин',
    'Пищевое производство',
    'Освежители и поглотители',
    'Мыло',
    'Антисептики',
    'Для машины',
    'Масла и смазки',
    'Деревообработка',
})

RELATED_CHEMISTRY: dict[str, frozenset[str]] = {
    'Общая уборка': frozenset({
        'Общая уборка', 'Химчистка', 'Пищевое производство',
    }),
    'Химчистка': frozenset({'Химчистка', 'Общая уборка', 'Для стирки'}),
    'Для стирки': frozenset({'Для стирки', 'Химчистка'}),
    'Для посудомоечных машин': frozenset({'Для посудомоечных машин', 'Пищевое производство'}),
    'Пищевое производство': frozenset({
        'Пищевое производство', 'Общая уборка', 'Для посудомоечных машин',
    }),
    'Мыло': frozenset({'Мыло', 'Антисептики'}),
    'Антисептики': frozenset({'Антисептики', 'Мыло'}),
    'Освежители и поглотители': frozenset({'Освежители и поглотители', 'Общая уборка'}),
    'Для машины': frozenset({'Для машины', 'Масла и смазки'}),
    'Масла и смазки': frozenset({'Масла и смазки', 'Для машины'}),
    'Деревообработка': frozenset({'Деревообработка'}),
    'Сопутствующие товары': frozenset(CHEMISTRY_CATEGORIES),
}


@dataclass
class RecommendationSet:
    similar: list[Product]
    bought_together: list[Product]

    def all(self) -> list[Product]:
        seen: set[int] = set()
        out: list[Product] = []
        for p in self.bought_together + self.similar:
            if p.id in seen:
                continue
            seen.add(p.id)
            out.append(p)
        return out


def _text_blob(product: Product) -> str:
    parts = [
        product.name or '',
        (product.description or '')[:400],
        product.category.name if product.category_id else '',
    ]
    return ' '.join(parts).casefold()


def _is_stop_product(product: Product) -> bool:
    blob = _text_blob(product)
    return any(word in blob for word in STOP_WORDS)


def _brand_token(name: str) -> str:
    name = (name or '').strip()
    if not name:
        return ''
    m = re.match(r'^([A-Za-zА-Яа-яЁё0-9]+)', name)
    return m.group(1).casefold() if m else ''


def _line_token(name: str) -> str:
    name = (name or '').strip()
    if not name:
        return ''
    base = re.split(r'\s*[\(\[]', name, maxsplit=1)[0].strip()
    base = re.sub(
        r'\s+\d+[.,]?\d*\s*(л|л\.|кг|кг\.|мл|шт|гр|г)\b.*$',
        '',
        base,
        flags=re.IGNORECASE,
    )
    base = re.sub(r'\s+\d+[.,]?\d*\s*$', '', base).strip()
    return base.casefold()


def pack_family_key(name: str) -> str:
    return _line_token(name)


def _affinity_group(product: Product) -> str | None:
    blob = _text_blob(product)
    for group, keywords in AFFINITY_GROUPS.items():
        if any(kw in blob for kw in keywords):
            return group
    return None


def _accessory_role(product: Product) -> str | None:
    name = (product.name or '').casefold()
    cat = (product.category.name if product.category_id else '').casefold()
    in_accessory_cat = 'сопутствующ' in cat

    for role, keywords in ACCESSORY_ROLES.items():
        if any(kw in name for kw in keywords):
            return role

    if in_accessory_cat:
        desc = (product.description or '')[:200].casefold()
        for role, keywords in ACCESSORY_ROLES.items():
            if any(kw in desc for kw in keywords):
                return role
        return 'accessory_generic'

    if any(kw in name for kw in ACCESSORY_ROLES['mop']):
        return 'mop'
    if any(kw in name for kw in ('тряпк', 'микрофибр')):
        return 'cloth'
    return None


def product_role(product: Product) -> str:
    group = _affinity_group(product)
    cat = product.category.name if product.category_id else ''
    if group in ('dishwash', 'laundry', 'soap', 'sanitizer', 'auto', 'descaler', 'degreaser', 'freshener'):
        acc_name = _accessory_role(product)
        if acc_name and acc_name != 'accessory_generic' and any(
            kw in (product.name or '').casefold()
            for role_kw in ACCESSORY_ROLES.values()
            for kw in role_kw
        ):
            return 'accessory'
        return group

    acc = _accessory_role(product)
    if acc:
        return 'accessory'
    if cat in CHEMISTRY_CATEGORIES:
        return 'chemistry'
    if cat == 'Сопутствующие товары':
        return 'accessory'
    return 'chemistry'


def _visible_qs() -> QuerySet[Product]:
    return Product.objects.filter(is_visible=True).select_related('category').prefetch_related('images')


def _take_unique(
    candidates: Iterable[Product],
    picked: list[Product],
    seen: set[int],
    limit: int,
) -> None:
    if limit <= 0:
        return
    for p in candidates:
        if p.id in seen or _is_stop_product(p):
            continue
        seen.add(p.id)
        picked.append(p)
        if len(picked) >= limit:
            return


def _codes_filter(codes: set[int]) -> Q:
    """Точное совпадение номера в списке '1,3,10' без ложного '1'→'10'."""
    parts = []
    for code in codes:
        parts.append(Q(recommendation_codes__regex=rf'(^|,){code}(,|$)'))
    return reduce(operator.or_, parts)


def products_by_recommendation_codes(
    product: Product,
    *,
    exclude_ids: set[int] | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[Product]:
    """Товары, у которых есть хотя бы один общий номер рекомендации."""
    codes = product.get_recommendation_code_set()
    if not codes or limit <= 0:
        return []

    exclude = set(exclude_ids or ()) | {product.id}
    qs = (
        _visible_qs()
        .exclude(id__in=exclude)
        .exclude(recommendation_codes='')
        .filter(_codes_filter(codes))
        .order_by('name')
    )

    picked: list[Product] = []
    seen = set(exclude)
    own = codes
    for candidate in qs[: max(limit * 4, 40)]:
        if candidate.id in seen or _is_stop_product(candidate):
            continue
        if not (own & candidate.get_recommendation_code_set()):
            continue
        seen.add(candidate.id)
        picked.append(candidate)
        if len(picked) >= limit:
            break
    return picked


def _similar_products(product: Product, exclude: set[int], limit: int) -> list[Product]:
    if limit <= 0:
        return []
    line = _line_token(product.name)
    brand = _brand_token(product.name)
    cat = product.category.name if product.category_id else ''
    related = RELATED_CHEMISTRY.get(cat, CHEMISTRY_CATEGORIES)

    base = _visible_qs().exclude(id__in=exclude | {product.id})
    base = base.exclude(category__name='Сопутствующие товары')

    picked: list[Product] = []
    seen = set(exclude) | {product.id}

    if line:
        _take_unique(
            base.filter(name__icontains=line).order_by('name')[:20],
            picked,
            seen,
            limit,
        )
    if len(picked) < limit and brand and len(brand) >= 2:
        chem = base.filter(category__name__in=related) if related else base
        _take_unique(
            chem.filter(name__istartswith=brand).order_by('name')[:20],
            picked,
            seen,
            limit,
        )
    return picked[:limit]


def _accessories_by_roles(roles: tuple[str, ...], exclude: set[int], limit: int) -> list[Product]:
    if limit <= 0 or not roles:
        return []
    base = _visible_qs().exclude(id__in=exclude)
    accessories = list(
        base.filter(category__name='Сопутствующие товары').order_by('name')[:80]
    )
    extras = list(
        base.exclude(category__name='Сопутствующие товары')
        .filter(
            Q(name__icontains='тряп')
            | Q(name__icontains='перчат')
            | Q(name__icontains='дозатор')
            | Q(name__icontains='ведро')
            | Q(name__icontains='vileda')
            | Q(name__icontains='микрофибр')
            | Q(name__icontains='швабр')
        )
        .order_by('name')[:40]
    )
    accessories = accessories + extras

    by_role: dict[str, list[Product]] = {r: [] for r in roles}
    for p in accessories:
        if _is_stop_product(p):
            continue
        role = _accessory_role(p)
        if role == 'accessory_generic':
            role = 'cloth'
        if role in by_role:
            by_role[role].append(p)

    picked: list[Product] = []
    seen = set(exclude)
    for role in roles:
        if len(picked) >= limit:
            break
        for p in by_role.get(role, []):
            if p.id in seen:
                continue
            seen.add(p.id)
            picked.append(p)
            break
    if len(picked) < limit:
        for role in roles:
            if len(picked) >= limit:
                break
            for p in by_role.get(role, []):
                if p.id in seen:
                    continue
                seen.add(p.id)
                picked.append(p)
                break
    return picked[:limit]


def _affinity_chemistry(product: Product, exclude: set[int], limit: int) -> list[Product]:
    if limit <= 0:
        return []
    group = _affinity_group(product)
    if not group:
        return []
    keywords = AFFINITY_GROUPS[group]
    cat = product.category.name if product.category_id else ''
    related = RELATED_CHEMISTRY.get(cat, CHEMISTRY_CATEGORIES)
    q = Q()
    for kw in keywords:
        q |= Q(name__icontains=kw) | Q(description__icontains=kw)
    qs = (
        _visible_qs()
        .exclude(id__in=exclude | {product.id})
        .exclude(category__name='Сопутствующие товары')
        .filter(category__name__in=related)
        .filter(q)
        .order_by('-is_featured', 'name')[:30]
    )
    picked: list[Product] = []
    seen = set(exclude) | {product.id}
    _take_unique(qs, picked, seen, limit)
    return picked


def _chemistry_for_accessory(product: Product, exclude: set[int], limit: int) -> list[Product]:
    if limit <= 0:
        return []
    qs = (
        _visible_qs()
        .exclude(id__in=exclude | {product.id})
        .filter(category__name__in=('Общая уборка', 'Пищевое производство', 'Химчистка'))
        .order_by('-is_featured', '-is_promo', 'name')[:40]
    )
    picked: list[Product] = []
    seen = set(exclude) | {product.id}
    _take_unique(qs, picked, seen, limit)
    return picked


def get_recommendations_for_product(product: Product, limit: int = DEFAULT_LIMIT) -> RecommendationSet:
    """
    Приоритет: общие номера «Рекомендация».
    Если номеров нет — запасной автоподбор (линейка / инвентарь).
    """
    coded = products_by_recommendation_codes(product, limit=limit)
    if coded:
        # Все связанные по номерам — в «С этим товаром обычно берут»
        return RecommendationSet(similar=[], bought_together=coded[:limit])

    role = product_role(product)
    similar_budget = 2
    accessories_budget = 4
    affinity_budget = 2

    similar = _similar_products(product, {product.id}, similar_budget)
    exclude_together = {product.id} | {p.id for p in similar}
    bought: list[Product] = []
    seen_together = set(exclude_together)

    if role == 'accessory':
        chem = _chemistry_for_accessory(product, seen_together, accessories_budget)
        _take_unique(chem, bought, seen_together, accessories_budget)
    else:
        target_roles = CROSS_SELL.get(role) or CROSS_SELL['chemistry']
        acc = _accessories_by_roles(target_roles, seen_together, accessories_budget)
        _take_unique(acc, bought, seen_together, accessories_budget)

    if role != 'accessory':
        aff = _affinity_chemistry(product, seen_together | {s.id for s in similar}, affinity_budget)
        _take_unique(aff, bought, seen_together, affinity_budget)

    similar = similar[:3]
    bought = bought[: max(4, limit - len(similar))]
    return RecommendationSet(similar=similar, bought_together=bought)


def get_recommendations_for_products(
    products: Iterable[Product],
    *,
    exclude_ids: Iterable[int] | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[Product]:
    """Для корзины — сначала по общим номерам, затем запасной автоподбор."""
    exclude = set(exclude_ids or [])
    collected: list[Product] = []
    seen: set[int] = set(exclude)

    for product in products:
        seen.add(product.id)
        coded = products_by_recommendation_codes(
            product,
            exclude_ids=seen,
            limit=limit - len(collected),
        )
        for rec in coded:
            if rec.id in seen:
                continue
            seen.add(rec.id)
            collected.append(rec)
            if len(collected) >= limit:
                return collected[:limit]

    if len(collected) >= limit:
        return collected[:limit]

    for product in products:
        seen.add(product.id)
        bundle = get_recommendations_for_product(product, limit=limit)
        for rec in bundle.bought_together + bundle.similar:
            if rec.id in seen or _is_stop_product(rec):
                continue
            seen.add(rec.id)
            collected.append(rec)
            if len(collected) >= limit:
                return collected[:limit]
    return collected[:limit]
