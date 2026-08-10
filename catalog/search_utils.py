"""Варианты поискового запроса: RU/EN транслит, раскладка, поиск по описанию."""

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

_SEARCH_FIELD = 'search_text'


def build_product_search_text(
    *,
    name: str = '',
    short_description: str = '',
    description: str = '',
    sku: str = '',
    country: str = '',
) -> str:
    """Нормализованный текст для поиска без учёта регистра (SQLite + кириллица)."""
    parts = (name, short_description, description, sku, country)
    return ' '.join(p.strip() for p in parts if p and p.strip()).casefold()


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


def query_tokens(q: str) -> list[str]:
    """Слова запроса (от 2 символов)."""
    return [t for t in re.split(r'[\s,;]+', (q or '').strip()) if len(t) >= 2]


def stem_variants(word: str) -> list[str]:
    """Варианты слова с укороченным окончанием (пятновыводитель / пятновыводители)."""
    w = (word or '').strip()
    if not w:
        return []
    stems = [w]
    if len(w) >= 6:
        stems.append(w[:-1])
    if len(w) >= 8:
        stems.append(w[:-2])
    seen = set()
    result = []
    for stem in stems:
        key = stem.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(stem)
    return result


def name_prefix_q(variants: list[str]) -> Q:
    """Совпадение с началом названия или началом слова в названии."""
    filt = Q()
    for v in variants:
        fold = v.casefold()
        if not fold:
            continue
        filt |= Q(**{f'{_SEARCH_FIELD}__startswith': fold})
        filt |= Q(**{f'{_SEARCH_FIELD}__contains': f' {fold}'})
        filt |= Q(**{f'{_SEARCH_FIELD}__contains': f'({fold}'})
        filt |= Q(**{f'{_SEARCH_FIELD}__contains': f'-{fold}'})
    return filt


def _term_in_text_q(term: str) -> Q:
    """Термин в названии или описании (с вариантами раскладки и окончаний)."""
    filt = Q()
    for variant in query_variants(term):
        for stem in stem_variants(variant):
            fold = stem.casefold()
            if fold:
                filt |= Q(**{f'{_SEARCH_FIELD}__contains': fold})
    return filt


def text_search_q(q: str) -> Q:
    """
    Поиск по названию и описанию.
    Несколько слов — каждое должно встретиться хотя бы в одном из полей.
    """
    tokens = query_tokens(q)
    if not tokens:
        variants = query_variants(q)
        if not variants:
            return Q()
        tokens = [variants[0]]

    combined = Q()
    for token in tokens:
        combined &= _term_in_text_q(token)
    return combined


def description_search_q(q: str) -> Q:
    """Вхождение запроса в описании или других полях (для подсказок)."""
    filt = Q()
    for token in query_tokens(q) or [q.strip()]:
        for variant in query_variants(token):
            for stem in stem_variants(variant):
                fold = stem.casefold()
                if fold:
                    filt |= Q(**{f'{_SEARCH_FIELD}__contains': fold})
    return filt


def filter_products_by_query(qs, q: str, *, prefix_only: bool = False):
    """
    Фильтр товаров по запросу.
    prefix_only=True — подсказки: префикс названия или совпадение в описании.
    """
    q = (q or '').strip()
    variants = query_variants(q)
    if not variants:
        return qs.none() if prefix_only else qs

    if prefix_only:
        return qs.filter(name_prefix_q(variants) | description_search_q(q))

    return qs.filter(name_prefix_q(variants) | text_search_q(q))


def rank_prefix_first(products, q: str):
    """Сортировка: название → краткое описание → полное описание."""
    variants = [v.casefold() for v in query_variants(q)]
    tokens = query_tokens(q) or ([q.strip()] if q.strip() else [])
    token_variants = []
    for token in tokens:
        token_variants.extend(v.casefold() for v in query_variants(token))
    if not token_variants:
        token_variants = variants

    def score(product):
        name = (product.name or '').casefold()
        short = (product.short_description or '').casefold()
        desc = (product.description or '').casefold()

        for i, v in enumerate(variants):
            if name.startswith(v):
                return (0, i, name)
            if re.search(rf'(^|[\s(\-]){re.escape(v)}', name):
                return (1, i, name)
            if v in name:
                return (2, i, name)

        for i, v in enumerate(variants):
            if v in short:
                return (3, i, name)
            if v in desc:
                return (4, i, name)

        for i, v in enumerate(token_variants):
            for stem in stem_variants(v):
                s = stem.casefold()
                if s in short:
                    return (5, i, name)
                if s in desc:
                    return (6, i, name)

        return (7, 99, name)

    return sorted(list(products), key=score)
