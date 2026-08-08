"""Варианты поискового запроса: RU/EN транслит и раскладка клавиатуры."""

from __future__ import annotations

import re
from django.db.models import Q

# ЙЦУКЕН <-> QWERTY (одна клавиша = один символ)
_LAYOUT_RU = "йцукенгшщзхъфывапролджэячсмитьбюё"
_LAYOUT_EN = "qwertyuiop[]asdfghjkl;'zxcvbnm,.`"
_RU_TO_EN_LAYOUT = str.maketrans(_LAYOUT_RU + _LAYOUT_RU.upper(), _LAYOUT_EN + _LAYOUT_EN.upper())
_EN_TO_RU_LAYOUT = str.maketrans(_LAYOUT_EN + _LAYOUT_EN.upper(), _LAYOUT_RU + _LAYOUT_RU.upper())

# Транслитерация (упрощённая, для префиксного поиска брендов)
_RU_TO_LATIN = [
    ('щ', 'sch'), ('ш', 'sh'), ('ч', 'ch'), ('ж', 'zh'), ('ю', 'yu'), ('я', 'ya'),
    ('ё', 'e'), ('й', 'y'), ('ц', 'ts'), ('х', 'h'), ('ъ', ''), ('ь', ''),
    ('а', 'a'), ('б', 'b'), ('в', 'v'), ('г', 'g'), ('д', 'd'), ('е', 'e'),
    ('з', 'z'), ('и', 'i'), ('к', 'k'), ('л', 'l'), ('м', 'm'), ('н', 'n'),
    ('о', 'o'), ('п', 'p'), ('р', 'r'), ('с', 's'), ('т', 't'), ('у', 'u'),
    ('ф', 'f'), ('ы', 'y'), ('э', 'e'),
]

_LATIN_TO_RU = [
    ('sch', 'щ'), ('sh', 'ш'), ('ch', 'ч'), ('zh', 'ж'), ('yu', 'ю'), ('ya', 'я'),
    ('ts', 'ц'),
    ('a', 'а'), ('b', 'б'), ('v', 'в'), ('g', 'г'), ('d', 'д'), ('e', 'е'),
    ('z', 'з'), ('i', 'и'), ('y', 'й'), ('k', 'к'), ('l', 'л'), ('m', 'м'),
    ('n', 'н'), ('o', 'о'), ('p', 'п'), ('r', 'р'), ('s', 'с'), ('t', 'т'),
    ('u', 'у'), ('f', 'ф'), ('h', 'х'),
]


def _transliterate_ru_to_en(text: str) -> str:
    lower = text.lower()
    out = []
    i = 0
    while i < len(lower):
        matched = False
        for src, dst in _RU_TO_LATIN:
            if lower.startswith(src, i):
                out.append(dst)
                i += len(src)
                matched = True
                break
        if not matched:
            out.append(lower[i])
            i += 1
    return ''.join(out)


def _transliterate_en_to_ru(text: str) -> str:
    lower = text.lower()
    out = []
    i = 0
    while i < len(lower):
        matched = False
        for src, dst in _LATIN_TO_RU:
            if lower.startswith(src, i):
                out.append(dst)
                i += len(src)
                matched = True
                break
        if not matched:
            out.append(lower[i])
            i += 1
    return ''.join(out)


def query_variants(q: str) -> list[str]:
    """Уникальные варианты запроса для RU/EN поиска."""
    q = (q or '').strip()
    if not q:
        return []
    variants = [
        q,
        q.translate(_RU_TO_EN_LAYOUT),
        q.translate(_EN_TO_RU_LAYOUT),
        _transliterate_ru_to_en(q),
        _transliterate_en_to_ru(q),
    ]
    # Убрать пустые и дубли (без учёта регистра)
    seen = set()
    result = []
    for v in variants:
        v = v.strip()
        if not v:
            continue
        key = v.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(v)
    return result


def name_prefix_q(variants: list[str]) -> Q:
    """Совпадение с началом названия или началом слова в названии."""
    filt = Q()
    for v in variants:
        filt |= Q(name__istartswith=v)
        # начало слова после пробела / скобки / дефиса
        filt |= Q(name__icontains=f' {v}')
        filt |= Q(name__icontains=f'({v}')
        filt |= Q(name__icontains=f'-{v}')
    return filt


def filter_products_by_query(qs, q: str, *, prefix_only: bool = False):
    """
    Фильтр товаров по запросу.
    prefix_only=True — только начало названия (для автоподсказок).
    """
    variants = query_variants(q)
    if not variants:
        return qs.none() if prefix_only else qs

    prefix = name_prefix_q(variants)
    if prefix_only:
        return qs.filter(prefix)

    # Полный поиск: сначала префикс названия, плюс вхождение в описание
    broad = Q()
    for v in variants:
        broad |= (
            Q(name__icontains=v)
            | Q(short_description__icontains=v)
            | Q(description__icontains=v)
        )
    return qs.filter(prefix | broad)


def rank_prefix_first(products, q: str):
    """Сортировка: сначала точное начало названия, затем остальные."""
    variants = [v.casefold() for v in query_variants(q)]
    if not variants:
        return list(products)

    def score(product):
        name = (product.name or '').casefold()
        for i, v in enumerate(variants):
            if name.startswith(v):
                return (0, i, name)
            if re.search(rf'(^|[\s(\-]){re.escape(v)}', name):
                return (1, i, name)
        return (2, 99, name)

    return sorted(list(products), key=score)
