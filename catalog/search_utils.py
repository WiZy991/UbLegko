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


def _normalize_search_blob(text: str) -> str:
    """Пробелы вместо пунктуации; края с пробелами — чтобы искать целые слова."""
    text = (text or '').casefold().replace('ё', 'е')
    # буквы/цифры/дефис оставляем, остальное — разделители слов
    text = re.sub(r'[^\w\-]+', ' ', text, flags=re.UNICODE)
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return ''
    return f' {text} '


def build_product_search_text(
    *,
    name: str = '',
    description: str = '',
    sku: str = '',
    country: str = '',
    short_description: str = '',  # совместимость со старыми вызовами
    category_name: str = '',  # совместимость; в индекс не входит
) -> str:
    """
    Нормализованный текст для поиска (название, описание, артикул, страна).
    SEO-фразы сюда не кладём — иначе запросы вроде «для пола» находят весь каталог.
    """
    parts = (name, description, sku, country, short_description)
    base = ' '.join(p.strip() for p in parts if p and p.strip())
    if not base:
        return ''
    blob = _normalize_search_blob(base)
    # Дополнительно склеенный вариант без дефисов/пробелов (sr-100 → sr100)
    mashed = re.sub(r'[\s\-]+', '', blob).strip()
    if mashed and f' {mashed} ' not in blob:
        blob = f'{blob}{mashed} '
    return blob


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


def _hyphen_space_variants(text: str) -> list[str]:
    """
    Варианты вокруг дефиса: «sr-100» ↔ «sr -100» (как в Bahler SR -100).
    """
    text = (text or '').strip()
    if not text or ('-' not in text and ' -' not in text):
        return []
    compact = re.sub(r'\s*-\s*', '-', text)
    compact = re.sub(r'\s+', ' ', compact).strip()
    # В каталоге часто «SR -100» (пробел перед дефисом)
    spaced = compact.replace('-', ' -')
    mashed = re.sub(r'[\s\-]+', '', compact)
    out = []
    for v in (compact, spaced, mashed):
        v = v.strip()
        if v and v.casefold() != text.casefold():
            out.append(v)
    return out


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
    expanded = []
    for v in variants:
        expanded.append(v)
        expanded.extend(_hyphen_space_variants(v))
    seen = set()
    result = []
    for v in expanded:
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
    """Совпадение с началом названия или началом слова (по search_text с пробелами по краям)."""
    filt = Q()
    for v in variants:
        fold = v.casefold().replace('ё', 'е')
        if not fold:
            continue
        # целое слово или префикс слова после разделителя
        filt |= Q(**{f'{_SEARCH_FIELD}__contains': f' {fold}'})
    return filt


def _term_in_text_q(term: str) -> Q:
    """
    Термин как целое слово (не кусок «ополаскиватель» для «пола»).
    Укороченные основы (от 6 букв) — префикс слова: пятновыводител → пятновыводитель.
    """
    filt = Q()
    for variant in query_variants(term):
        stems = stem_variants(variant)
        if not stems:
            continue
        full = stems[0].casefold().replace('ё', 'е')
        if full:
            # только целое слово
            filt |= Q(**{f'{_SEARCH_FIELD}__contains': f' {full} '})
        for stem in stems[1:]:
            fold = stem.casefold().replace('ё', 'е')
            if fold:
                # префикс слова после пробела
                filt |= Q(**{f'{_SEARCH_FIELD}__contains': f' {fold}'})
    return filt


def text_search_q(q: str) -> Q:
    """
    Поиск по названию и описанию.
    Несколько слов — каждое должно встретиться как целое слово.
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
    """Вхождение запроса в тексте товара (для подсказок) — те же правила, что у поиска."""
    return text_search_q(q)


def filter_products_by_query(qs, q: str, *, prefix_only: bool = False):
    """
    Фильтр товаров по запросу (только реальный текст товара: имя, описание, артикул).
    Несколько слов — каждое слово должно встретиться в тексте.
    prefix_only=True — подсказки: префикс названия или совпадение в тексте.
    """
    q = (q or '').strip()
    variants = query_variants(q)
    if not variants:
        return qs.none() if prefix_only else qs

    if prefix_only:
        return qs.filter(name_prefix_q(variants) | description_search_q(q)).distinct()

    return qs.filter(text_search_q(q)).distinct()


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
        desc = (product.description or '').casefold()

        for i, v in enumerate(variants):
            if name.startswith(v):
                return (0, i, name)
            if re.search(rf'(^|[\s(\-]){re.escape(v)}', name):
                return (1, i, name)
            if v in name:
                return (2, i, name)

        for i, v in enumerate(variants):
            if v in desc:
                return (3, i, name)

        for i, v in enumerate(token_variants):
            for stem in stem_variants(v):
                s = stem.casefold()
                if s in desc:
                    return (4, i, name)

        return (5, 99, name)

    return sorted(list(products), key=score)
