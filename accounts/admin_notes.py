"""Админские заметки «кто это» — только для персонала, клиент не видит."""

from __future__ import annotations

from django.utils.html import escape, mark_safe


def get_admin_note_for_user(user) -> str:
    if user is None:
        return ''
    profile = getattr(user, 'profile', None)
    if profile is None:
        return ''
    return (getattr(profile, 'admin_note', None) or '').strip()


def get_admin_note_for_contact(*, user=None, phone: str = '') -> str:
    """Заметка по пользователю заявки или по совпадению телефона."""
    note = get_admin_note_for_user(user)
    if note:
        return note
    phone = (phone or '').strip()
    if not phone:
        return ''
    from .models import Profile

    return (
        Profile.objects.filter(phone=phone)
        .exclude(admin_note='')
        .values_list('admin_note', flat=True)
        .first()
        or ''
    ).strip()


def format_name_with_admin_note(name: str, note: str = '') -> str:
    name = (name or '').strip() or '—'
    note = (note or '').strip()
    if note:
        return f'{name} ({note})'
    return name


def name_with_admin_note_html(name: str, note: str = ''):
    name = (name or '').strip() or '—'
    note = (note or '').strip()
    if not note:
        return escape(name)
    return mark_safe(
        f'{escape(name)} <span class="admin-user-note">({escape(note)})</span>'
    )
