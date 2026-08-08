"""Рекомендации в духе Amazon: похожие (линейка) + «с этим берут» (инвентарь/комплект)."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from django.db.models import Q, QuerySet

from .models import Product, ProductRecommendation

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

# Узкие группы назначения химии
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

# Роли инвентаря (часто покупают вместе с химией)
ACCESSORY_ROLES: dict[str, tuple[str, ...]] = {
    'cloth': ('тряпк', 'салфет', 'микрофибр', 'губка', 'губки', 'wipe'),
    'glove': ('перчатк',),
    'dispenser': ('дозатор', 'распыл', 'пульвериз', 'триггер'),
    'bucket': ('ведро',),
    'mop': ('vileda', 'швабр', 'насадк', 'ultramax', 'моп'),
}

# Роль источника → какие роли инвентаря подбирать в «bought together»
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
    'accessory': (),  # обратный кросс-селл отдельно
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
        product.short_description or '',
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
    """Роль инвентаря. Химию с упоминанием «дозатор» в описании не считаем инвентарём."""
    name = (product.name or '').casefold()
    cat = (product.category.name if product.category_id else '').casefold()
    in_accessory_cat = 'сопутствующ' in cat
    blob_name = name  # только название — надёжнее описания

    for role, keywords in ACCESSORY_ROLES.items():
        if any(kw in blob_name for kw in keywords):
            return role

    # В категории сопутствующих без явного типа
    if in_accessory_cat:
        # описание только внутри категории инвентаря
        desc = ((product.short_description or '') + ' ' + (product.description or '')[:200]).casefold()
        for role, keywords in ACCESSORY_ROLES.items():
            if any(kw in desc for kw in keywords):
                return role
        return 'accessory_generic'

    # Vileda / моп могут лежать в «Общая уборка»
    if any(kw in name for kw in ACCESSORY_ROLES['mop']):
        return 'mop'
    if any(kw in name for kw in ('тряпк', 'микрофибр')):
        return 'cloth'
    return None


def product_role(product: Product) -> str:
    """Главная роль товара для кросс-сейла."""
    # Сначала узкая химия по категории/affinity — чтобы Dishwash не стал «accessory»
    group = _affinity_group(product)
    cat = product.category.name if product.category_id else ''
    if group in ('dishwash', 'laundry', 'soap', 'sanitizer', 'auto', 'descaler', 'degreaser', 'freshener'):
        # если это явно инвентарь по названию — всё же accessory
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
    return Product.objects.filter(is_visible=True).select_related('category')


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


def _manual_links(product: Product, limit: int) -> list[Product]:
    forward = (
        ProductRecommendation.objects.filter(product=product)
        .select_related('recommended_product', 'recommended_product__category')
        .filter(recommended_product__is_visible=True)
        .exclude(recommended_product_id=product.id)
        .order_by('sort_order', 'id')
    )
    reverse = (
        ProductRecommendation.objects.filter(recommended_product=product)
        .select_related('product', 'product__category')
        .filter(product__is_visible=True)
        .exclude(product_id=product.id)
        .order_by('sort_order', 'id')
    )
    result: list[Product] = []
    seen: set[int] = {product.id}
    for row in forward:
        p = row.recommended_product
        if p.id in seen or _is_stop_product(p):
            continue
        seen.add(p.id)
        result.append(p)
        if len(result) >= limit:
            return result
    for row in reverse:
        p = row.product
        if p.id in seen or _is_stop_product(p):
            continue
        seen.add(p.id)
        result.append(p)
        if len(result) >= limit:
            return result
    return result


def _similar_products(product: Product, exclude: set[int], limit: int) -> list[Product]:
    """Похожие: фасовки линейки, затем бренд в родственной химии."""
    if limit <= 0:
        return []
    line = _line_token(product.name)
    brand = _brand_token(product.name)
    cat = product.category.name if product.category_id else ''
    related = RELATED_CHEMISTRY.get(cat, CHEMISTRY_CATEGORIES)

    base = _visible_qs().exclude(id__in=exclude | {product.id})
    # Похожие — химия, не инвентарь
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
    """По одной позиции каждого типа инвентаря (тряпка, перчатки, дозатор…)."""
    if limit <= 0 or not roles:
        return []
    base = _visible_qs().exclude(id__in=exclude)
    # Сначала категория сопутствующих, затем явный инвентарь по названию
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
        q |= Q(name__icontains=kw) | Q(short_description__icontains=kw) | Q(description__icontains=kw)
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
    """Обратный кросс-селл: к тряпке/дозатору — популярная химия для уборки."""
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
    Amazon-стиль:
    - similar: фасовки / бренд
    - bought_together: ручные связи + инвентарь по матрице + affinity-химия
    """
    role = product_role(product)
    manual = _manual_links(product, limit=4)

    similar_budget = 2
    accessories_budget = 4
    affinity_budget = 2

    exclude_similar = {product.id}
    similar = _similar_products(product, exclude_similar, similar_budget)

    exclude_together = {product.id} | {p.id for p in similar} | {p.id for p in manual}
    bought: list[Product] = []
    seen_together = set(exclude_together)

    # 1) Ручные комплементы — в начало «с этим берут»
    for p in manual:
        if p.id in seen_together or _is_stop_product(p):
            continue
        # Ручные, которые сами по себе «похожие» (та же линейка), лучше в similar
        if _line_token(p.name) and _line_token(p.name) == _line_token(product.name):
            if len(similar) < similar_budget + 1 and p.id not in {s.id for s in similar}:
                similar.append(p)
            continue
        seen_together.add(p.id)
        bought.append(p)

    # 2) Инвентарь / обратный кросс-селл
    remaining = limit  # общий потолок на оба блока ниже проверим
    if role == 'accessory':
        chem = _chemistry_for_accessory(product, seen_together, accessories_budget)
        _take_unique(chem, bought, seen_together, accessories_budget)
    else:
        target_roles = CROSS_SELL.get(role) or CROSS_SELL['chemistry']
        acc = _accessories_by_roles(target_roles, seen_together, accessories_budget)
        _take_unique(acc, bought, seen_together, accessories_budget)

    # 3) Химия того же назначения
    if role != 'accessory':
        aff = _affinity_chemistry(product, seen_together | {s.id for s in similar}, affinity_budget)
        _take_unique(aff, bought, seen_together, affinity_budget)

    # Подрезать: similar до 3, bought_together до 5–6, суммарно ~limit+2
    similar = similar[:3]
    bought = bought[: max(4, limit - len(similar))]
    return RecommendationSet(similar=similar, bought_together=bought)


def get_recommendations_for_products(
    products: Iterable[Product],
    *,
    exclude_ids: Iterable[int] | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[Product]:
    """Для корзины — приоритет bought_together, затем similar."""
    exclude = set(exclude_ids or [])
    collected: list[Product] = []
    seen: set[int] = set(exclude)

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
