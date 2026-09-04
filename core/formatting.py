"""Общее форматирование сумм и чисел."""

from decimal import Decimal, InvalidOperation


def format_rubles(value) -> str:
    """13520 → '13 520 руб'."""
    try:
        amount = Decimal(value or 0)
    except (InvalidOperation, TypeError, ValueError):
        amount = Decimal('0')
    whole = f'{amount:.0f}'
    grouped = f'{int(whole):,}'.replace(',', ' ')
    return f'{grouped} руб'
