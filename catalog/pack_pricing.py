"""Сравнение фасовок одной линейки (по артикулу: 034-1 / 034-5)."""

from __future__ import annotations

import re
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, NamedTuple

from .models import Product

# Объём в названии: «5л», «1 л», «(0,75л)», «0,5 л.».
_LITERS_RE = re.compile(
    r'(?<![A-Za-zА-Яа-яЁё])(\d+[.,]?\d*)\s*(?:л\.?|l)\b',
    re.IGNORECASE,
)

# Артикул: база + суффикс литража после последнего дефиса.
_SKU_RE = re.compile(r'^(?P<base>.+)-(?P<suffix>\d+)$')

# Однозначные суффиксы артикула → литры.
_SKU_LITERS = {
    '1': Decimal('1'),
    '3': Decimal('3'),
    '5': Decimal('5'),
    '01': Decimal('1'),
    '02': Decimal('0.2'),
    '04': Decimal('0.4'),
    '075': Decimal('0.75'),
    '005': Decimal('0.5'),
    '014': Decimal('1.4'),
    '025': Decimal('0.25'),
    '21': Decimal('20'),
    '22': Decimal('20'),
}


class PackUnitPrice(NamedTuple):
    """Цена меньшей фасовки в пересчёте с большей канистры."""

    unit_liters: Decimal
    unit_price: int

    @property
    def liters_display(self) -> str:
        return _format_liters(self.unit_liters)


def parse_liters(name: str) -> Decimal | None:
    if not name:
        return None
    match = _LITERS_RE.search(name)
    if not match:
        return None
    raw = match.group(1).replace(',', '.')
    try:
        value = Decimal(raw)
    except Exception:
        return None
    if value <= 0:
        return None
    return value


def split_sku(sku: str) -> tuple[str, str] | None:
    match = _SKU_RE.match((sku or '').strip())
    if not match:
        return None
    base = match.group('base').strip()
    suffix = match.group('suffix')
    if not base or not suffix:
        return None
    return base, suffix


def _format_liters(liters: Decimal) -> str:
    text = format(liters.normalize(), 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text.replace('.', ',')


def _liters_from_sku_suffix(suffix: str, family_suffixes: set[str]) -> Decimal | None:
    if suffix in _SKU_LITERS:
        return _SKU_LITERS[suffix]

    # «05» — чаще 0,5 л (034-05), у Bahler рядом с «01»/«005» бывает 5 л.
    if suffix == '05':
        if '5' in family_suffixes:
            return Decimal('0.5')
        if family_suffixes & {'005', '01', '21', '22'}:
            return Decimal('5')
        return Decimal('0.5')

    # «03» — 0,3 л (144-03) либо 3 л у Bahler (BTC-100-03).
    if suffix == '03':
        if '3' in family_suffixes:
            return Decimal('0.3')
        if family_suffixes & {'005', '01', '05', '21', '22'}:
            return Decimal('3')
        return Decimal('0.3')

    return None


def _unit_price(max_price: Decimal, max_liters: Decimal, unit_liters: Decimal) -> int:
    """Сколько стоит unit_liters, если брать большую канистру."""
    per = (max_price * unit_liters / max_liters).quantize(
        Decimal('1'), rounding=ROUND_HALF_UP
    )
    return int(per)


def build_price_per_liter_map(
    products: Iterable[tuple[int, str, Decimal, str]] | None = None,
) -> dict[int, PackUnitPrice]:
    """
    product_id → цена меньшей фасовки в пересчёте с этой канистры.

    Линейка = база артикула (FS-108-01 / FS-108-05 / FS-108-21).
    На каждой фасовке больше минимальной показываем
    «1л = Nр.» / «0,5л = Nр.» — объём от самой маленькой в линейке.
    """
    if products is None:
        products = Product.objects.filter(is_visible=True).values_list(
            'id', 'name', 'price', 'sku'
        )

    raw_families: dict[str, list[tuple[int, str, str, Decimal]]] = defaultdict(list)
    for product_id, name, price, sku in products:
        parts = split_sku(sku or '')
        if not parts:
            continue
        base, suffix = parts
        raw_families[base].append((product_id, name or '', suffix, Decimal(price)))

    result: dict[int, PackUnitPrice] = {}
    for items in raw_families.values():
        if len(items) < 2:
            continue

        family_suffixes = {suffix for _pid, _name, suffix, _price in items}
        sized: list[tuple[int, Decimal, Decimal]] = []
        for product_id, name, suffix, price in items:
            liters = parse_liters(name)
            if liters is None:
                liters = _liters_from_sku_suffix(suffix, family_suffixes)
            if liters is None:
                continue
            sized.append((product_id, liters, price))

        if len(sized) < 2:
            continue

        min_liters = min(liters for _pid, liters, _price in sized)
        max_liters = max(liters for _pid, liters, _price in sized)
        if min_liters >= max_liters:
            continue

        # Все фасовки крупнее минимальной — своя «выгода» (пересчёт в мин. объём)
        for product_id, liters, price in sized:
            if liters <= min_liters:
                continue
            result[product_id] = PackUnitPrice(
                unit_liters=min_liters,
                unit_price=_unit_price(price, liters, min_liters),
            )

    return result


def attach_price_per_liter(products: Iterable[Product] | None) -> None:
    """
    Проставляет на товаре:
    - price_per_liter — цена за объём меньшей фасовки (или None)
    - pack_unit_liters — строка объёма для подписи («0,3», «0,5», «1»)
    """
    if not products:
        return
    items = list(products)
    price_map = build_price_per_liter_map()
    for product in items:
        info = price_map.get(product.id)
        if info is None:
            product.price_per_liter = None
            product.pack_unit_liters = None
        else:
            product.price_per_liter = info.unit_price
            product.pack_unit_liters = info.liters_display
