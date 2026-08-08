"""Общие проверки телефона и email для форм сайта."""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError

PHONE_RE = re.compile(r'^\+7\d{10}$')
EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')
FAKE_EMAIL_DOMAINS = frozenset({
    'example.com',
    'example.ru',
    'test.com',
    'test.ru',
    'mail.mail',
    'asdf.asdf',
})


def normalize_ru_phone(value: str) -> str:
    """Приводит телефон к виду +7XXXXXXXXXX."""
    digits = re.sub(r'\D', '', value or '')
    if not digits:
        return ''
    if digits.startswith('8') and len(digits) == 11:
        digits = '7' + digits[1:]
    elif digits.startswith('7') and len(digits) == 11:
        pass
    elif len(digits) == 10:
        digits = '7' + digits
    else:
        return digits
    return f'+{digits}'


def format_ru_phone_display(normalized: str) -> str:
    """+79991234567 → +7 (999) 123-45-67"""
    digits = re.sub(r'\D', '', normalized or '')
    if len(digits) != 11 or not digits.startswith('7'):
        return normalized
    return f'+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}'


def clean_ru_phone(value: str) -> str:
    normalized = normalize_ru_phone(value)
    if not PHONE_RE.match(normalized):
        raise ValidationError('Укажите телефон в формате +7 (999) 000-00-00')
    return format_ru_phone_display(normalized)


def clean_user_email(value: str, *, required: bool = True) -> str:
    email = (value or '').strip()
    if not email:
        if required:
            raise ValidationError('Укажите email')
        return ''
    if not EMAIL_RE.match(email):
        raise ValidationError('Укажите корректный email, например name@mail.ru')
    domain = email.split('@', 1)[1].lower()
    if domain in FAKE_EMAIL_DOMAINS:
        raise ValidationError('Укажите существующий email для связи')
    if '..' in email or email.startswith('.') or email.endswith('.'):
        raise ValidationError('Укажите корректный email')
    return email.lower()
