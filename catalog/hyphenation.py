"""Переносы по правилам русского языка (мягкие переносы U+00AD)."""

from __future__ import annotations

import logging
import re
from functools import lru_cache

logger = logging.getLogger(__name__)

SOFT_HYPHEN = '\u00AD'

# Слова из букв (кириллица/латиница). Уже с дефисом не трогаем целиком — разобьём по частям.
_WORD_RE = re.compile(r'[A-Za-zА-Яа-яЁё]+(?:-[A-Za-zА-Яа-яЁё]+)*')


@lru_cache(maxsize=1)
def _dictionary():
    try:
        import pyphen
    except ImportError:
        logger.warning('pyphen не установлен — переносы в описаниях отключены')
        return None
    # Словари Hunspell/LibreOffice: left/right ≥ 2 — не оставлять одну букву
    try:
        return pyphen.Pyphen(lang='ru_RU', left=2, right=2)
    except Exception:
        try:
            return pyphen.Pyphen(lang='ru', left=2, right=2)
        except Exception:
            logger.exception('Не удалось загрузить словарь переносов ru')
            return None


def _hyphenate_token(token: str, dic) -> str:
    if len(token) < 5:
        return token
    if SOFT_HYPHEN in token:
        return token
    # Числа / артикулы вперемешку с буквами — не трогаем
    if any(ch.isdigit() for ch in token):
        return token

    # «чёрно-белый» — переносим каждую часть отдельно
    if '-' in token:
        return '-'.join(_hyphenate_token(part, dic) if part else part for part in token.split('-'))

    try:
        return dic.inserted(token, hyphen=SOFT_HYPHEN)
    except Exception:
        return token


def hyphenate_ru(text: str) -> str:
    """
    Вставляет мягкие переносы в русские слова.
    В браузере при нехватке ширины слово переносится со знаком «-».
    """
    if not text:
        return text
    dic = _dictionary()
    if dic is None:
        return text
    return _WORD_RE.sub(lambda m: _hyphenate_token(m.group(0), dic), text)
