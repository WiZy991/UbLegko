"""Упрощённые роли доступа и сегменты клиентов."""

from __future__ import annotations

from django.contrib.auth.models import Group, Permission, User
from django.db import transaction

# --- Роли доступа в админку ---
ROLE_ADMIN = 'admin'
ROLE_STAFF = 'staff'
ROLE_USER = 'user'

ROLE_CHOICES = (
    (ROLE_ADMIN, 'Администратор'),
    (ROLE_STAFF, 'Персонал'),
    (ROLE_USER, 'Пользователь'),
)

ROLE_LABELS = dict(ROLE_CHOICES)

GROUP_ADMIN = 'Администраторы'
GROUP_STAFF = 'Персонал'

# --- Сегменты клиентов (права как у обычного пользователя сайта) ---
SEGMENT_VIP = 'vip'
SEGMENT_REGULAR = 'regular'
SEGMENT_BASE = 'base'

SEGMENT_CHOICES = (
    ('', '— без сегмента'),
    (SEGMENT_VIP, 'VIP-клиенты'),
    (SEGMENT_REGULAR, 'Постоянные клиенты'),
    (SEGMENT_BASE, 'Клиенты'),
)

SEGMENT_LABELS = {key: label for key, label in SEGMENT_CHOICES if key}

GROUP_VIP = 'VIP-клиенты'
GROUP_REGULAR = 'Постоянные клиенты'
GROUP_BASE = 'Клиенты'

SEGMENT_GROUP_NAMES = {
    SEGMENT_VIP: GROUP_VIP,
    SEGMENT_REGULAR: GROUP_REGULAR,
    SEGMENT_BASE: GROUP_BASE,
}

ACCESS_GROUP_NAMES = {
    ROLE_ADMIN: GROUP_ADMIN,
    ROLE_STAFF: GROUP_STAFF,
}

ROLE_HELP = {
    ROLE_ADMIN: 'Полный доступ ко всей админке, настройкам и удалению.',
    ROLE_STAFF: (
        'Вход в админку: просмотр заявок и запросов, кнопки «Готово». '
        'Без удаления и без настроек сайта.'
    ),
    ROLE_USER: 'Обычный пользователь сайта без входа в админку.',
}

# Права персонала: заявки и запросы — смотреть и менять статус, без delete
STAFF_PERMISSION_CODES = (
    ('cart', 'view_order'),
    ('cart', 'change_order'),
    ('cart', 'view_orderitem'),
    ('cart', 'view_stainhelprequest'),
    ('cart', 'change_stainhelprequest'),
)


def get_staff_permissions():
    perms = []
    for app_label, codename in STAFF_PERMISSION_CODES:
        perm = Permission.objects.filter(
            content_type__app_label=app_label,
            codename=codename,
        ).first()
        if perm:
            perms.append(perm)
    return perms


def get_all_permissions():
    return list(Permission.objects.all())


def apply_permissions_for_role(group: Group, role: str) -> None:
    """Выставляет права группе по упрощённой роли."""
    if role == ROLE_ADMIN:
        group.permissions.set(get_all_permissions())
    elif role == ROLE_STAFF:
        group.permissions.set(get_staff_permissions())
    else:
        group.permissions.clear()


def detect_group_role(group: Group) -> str:
    """Угадывает роль группы по имени или набору прав."""
    name = (group.name or '').strip()
    if name == GROUP_ADMIN:
        return ROLE_ADMIN
    if name == GROUP_STAFF:
        return ROLE_STAFF
    if name in SEGMENT_GROUP_NAMES.values():
        return ROLE_USER

    codes = set(group.permissions.values_list('codename', flat=True))
    if not codes:
        return ROLE_USER
    staff_codes = {code for _app, code in STAFF_PERMISSION_CODES}
    if codes <= staff_codes and 'change_order' in codes and 'view_order' in codes:
        return ROLE_STAFF
    if group.permissions.count() >= Permission.objects.count() * 0.8:
        return ROLE_ADMIN
    return ROLE_USER


def detect_user_access_role(user: User) -> str:
    if user.is_superuser:
        return ROLE_ADMIN
    if user.is_staff:
        return ROLE_STAFF
    return ROLE_USER


def detect_user_segment(user: User) -> str:
    names = set(user.groups.values_list('name', flat=True))
    for key, group_name in SEGMENT_GROUP_NAMES.items():
        if group_name in names:
            return key
    return ''


def get_or_create_named_group(name: str) -> Group:
    group, _ = Group.objects.get_or_create(name=name)
    return group


@transaction.atomic
def ensure_default_groups() -> dict[str, Group]:
    """Создаёт стандартные группы с нужными правами."""
    result = {}

    admin_group = get_or_create_named_group(GROUP_ADMIN)
    apply_permissions_for_role(admin_group, ROLE_ADMIN)
    result[ROLE_ADMIN] = admin_group

    staff_group = get_or_create_named_group(GROUP_STAFF)
    apply_permissions_for_role(staff_group, ROLE_STAFF)
    result[ROLE_STAFF] = staff_group

    for key, name in SEGMENT_GROUP_NAMES.items():
        group = get_or_create_named_group(name)
        apply_permissions_for_role(group, ROLE_USER)
        result[key] = group

    return result


@transaction.atomic
def set_user_access_role(user: User, role: str, *, actor: User | None = None) -> None:
    """Назначает пользователю упрощённую роль доступа."""
    if role not in ROLE_LABELS:
        raise ValueError('Неизвестная роль')

    ensure_default_groups()

    # Нельзя снять себе админку
    if actor is not None and actor.pk == user.pk and role != ROLE_ADMIN and user.is_superuser:
        raise PermissionError('Нельзя понизить права своему аккаунту')

    # Убрать из групп доступа
    for group_name in ACCESS_GROUP_NAMES.values():
        group = Group.objects.filter(name=group_name).first()
        if group:
            user.groups.remove(group)

    user.user_permissions.clear()

    if role == ROLE_ADMIN:
        user.is_superuser = True
        user.is_staff = True
        user.save(update_fields=['is_superuser', 'is_staff'])
        user.groups.add(get_or_create_named_group(GROUP_ADMIN))
        return

    if role == ROLE_STAFF:
        user.is_superuser = False
        user.is_staff = True
        user.save(update_fields=['is_superuser', 'is_staff'])
        staff_group = get_or_create_named_group(GROUP_STAFF)
        apply_permissions_for_role(staff_group, ROLE_STAFF)
        user.groups.add(staff_group)
        return

    # Пользователь сайта
    user.is_superuser = False
    user.is_staff = False
    user.save(update_fields=['is_superuser', 'is_staff'])


@transaction.atomic
def set_user_segment(user: User, segment: str) -> None:
    """Назначает клиентский сегмент (взаимоисключающие группы)."""
    if segment not in SEGMENT_LABELS and segment != '':
        raise ValueError('Неизвестный сегмент')

    ensure_default_groups()

    for group_name in SEGMENT_GROUP_NAMES.values():
        group = Group.objects.filter(name=group_name).first()
        if group:
            user.groups.remove(group)

    if not segment:
        return

    group_name = SEGMENT_GROUP_NAMES[segment]
    group = get_or_create_named_group(group_name)
    apply_permissions_for_role(group, ROLE_USER)
    user.groups.add(group)


def format_user_groups_summary(user: User) -> str:
    role = ROLE_LABELS.get(detect_user_access_role(user), 'Пользователь')
    segment = SEGMENT_LABELS.get(detect_user_segment(user), '')
    if segment:
        return f'{role} · {segment}'
    return role
