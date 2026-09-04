"""Общее форматирование сумм и чисел."""

from decimal import Decimal, InvalidOperation


def format_grouped_number(value) -> str:
    """13520 → '13 520' (неразрывный пробел между разрядами)."""
    try:
        amount = Decimal(value or 0)
    except (InvalidOperation, TypeError, ValueError):
        amount = Decimal('0')
    whole = f'{amount:.0f}'
    # NBSP — пробел не схлопывается и лучше виден в вёрстке
    return f'{int(whole):,}'.replace(',', '\u00a0')


def format_rubles(value) -> str:
    """13520 → '13 520 руб'."""
    return f'{format_grouped_number(value)} руб'
