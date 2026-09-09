"""Упрощённые роли доступа и группы пользователей."""

from __future__ import annotations

from django.contrib.auth.models import Group, Permission, User
from django.db import transaction
from django.db.models import Q

# --- Роли доступа в админку ---
ROLE_ADMIN = 'admin'
ROLE_STAFF = 'staff'
ROLE_USER = 'user'
ROLE_BLOCKED = 'blocked'

ROLE_CHOICES = (
    (ROLE_ADMIN, 'Администратор'),
    (ROLE_STAFF, 'Персонал'),
    (ROLE_USER, 'Пользователь'),
    (ROLE_BLOCKED, 'Заблокированные'),
)

ROLE_LABELS = dict(ROLE_CHOICES)

# Роли для шаблона прав группы (без «Заблокированные»)
GROUP_ROLE_CHOICES = (
    (ROLE_ADMIN, 'Администратор'),
    (ROLE_STAFF, 'Персонал'),
    (ROLE_USER, 'Пользователь'),
)

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

# Единый выбор «Группа» в таблице пользователей (стандарт; + кастомные через get_membership_choices)
MEMBERSHIP_CHOICES = (
    ('', '— без сегмента'),
    (ROLE_ADMIN, GROUP_ADMIN),
    (ROLE_STAFF, GROUP_STAFF),
    (SEGMENT_VIP, GROUP_VIP),
    (SEGMENT_REGULAR, GROUP_REGULAR),
    (SEGMENT_BASE, GROUP_BASE),
)

MEMBERSHIP_LABELS = dict(MEMBERSHIP_CHOICES)

ALL_MANAGED_GROUP_NAMES = (
    GROUP_ADMIN,
    GROUP_STAFF,
    GROUP_VIP,
    GROUP_REGULAR,
    GROUP_BASE,
)

CUSTOM_GROUP_PREFIX = 'g:'

ROLE_HELP = {
    ROLE_ADMIN: 'Полный доступ ко всей админке, настройкам и удалению.',
    ROLE_STAFF: (
        'Вход в админку: просмотр заявок и запросов, кнопки «Готово». '
        'Без удаления и без настроек сайта.'
    ),
    ROLE_USER: 'Обычный пользователь сайта без входа в админку.',
    ROLE_BLOCKED: 'Вход на сайт запрещён, аккаунт отключён.',
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
    profile = getattr(user, 'profile', None)
    if profile is None:
        try:
            profile = user.profile
        except Exception:
            profile = None
    if profile is not None and getattr(profile, 'is_blocked', False):
        return ROLE_BLOCKED
    if user.is_superuser:
        return ROLE_ADMIN
    if user.is_staff:
        return ROLE_STAFF
    return ROLE_USER


def _set_user_blocked(user: User, blocked: bool) -> None:
    from .models import Profile

    profile, _ = Profile.objects.get_or_create(user=user)
    if profile.is_blocked != blocked:
        profile.is_blocked = blocked
        profile.save(update_fields=['is_blocked'])


def user_is_blocked(user: User) -> bool:
    if not getattr(user, 'is_authenticated', False):
        return False
    profile = getattr(user, 'profile', None)
    if profile is None:
        try:
            profile = user.profile
        except Exception:
            return False
    return bool(getattr(profile, 'is_blocked', False))


def _user_group_names(user: User) -> set[str]:
    if hasattr(user, '_prefetched_objects_cache') and 'groups' in user._prefetched_objects_cache:
        return {g.name for g in user.groups.all()}
    return set(user.groups.values_list('name', flat=True))


def detect_user_segment(user: User) -> str:
    names = _user_group_names(user)
    for key, group_name in SEGMENT_GROUP_NAMES.items():
        if group_name in names:
            return key
    return ''


def custom_membership_key(group_id: int) -> str:
    return f'{CUSTOM_GROUP_PREFIX}{int(group_id)}'


def parse_custom_membership(membership: str) -> int | None:
    if not membership or not str(membership).startswith(CUSTOM_GROUP_PREFIX):
        return None
    try:
        return int(str(membership)[len(CUSTOM_GROUP_PREFIX):])
    except (TypeError, ValueError):
        return None


def get_membership_choices() -> tuple[tuple[str, str], ...]:
    """Стандартные группы + все созданные вручную."""
    items: list[tuple[str, str]] = [
        ('', '— без сегмента'),
        (ROLE_ADMIN, GROUP_ADMIN),
        (ROLE_STAFF, GROUP_STAFF),
        (SEGMENT_VIP, GROUP_VIP),
        (SEGMENT_REGULAR, GROUP_REGULAR),
        (SEGMENT_BASE, GROUP_BASE),
    ]
    for group in Group.objects.exclude(name__in=ALL_MANAGED_GROUP_NAMES).order_by('name'):
        items.append((custom_membership_key(group.pk), group.name))
    return tuple(items)


def membership_label(key: str) -> str:
    return dict(get_membership_choices()).get(key, '— без сегмента')


def is_known_membership(membership: str) -> bool:
    if membership in MEMBERSHIP_LABELS:
        return True
    pk = parse_custom_membership(membership)
    if pk is None:
        return False
    return Group.objects.filter(pk=pk).exclude(name__in=ALL_MANAGED_GROUP_NAMES).exists()


def detect_user_membership(user: User) -> str:
    """Главная группа пользователя для колонки «Группа»."""
    names = _user_group_names(user)
    if user.is_superuser or GROUP_ADMIN in names:
        return ROLE_ADMIN
    if user.is_staff or GROUP_STAFF in names:
        return ROLE_STAFF
    for key, group_name in SEGMENT_GROUP_NAMES.items():
        if group_name in names:
            return key
    custom_names = names - set(ALL_MANAGED_GROUP_NAMES)
    if custom_names:
        group = Group.objects.filter(name__in=custom_names).order_by('name').first()
        if group:
            return custom_membership_key(group.pk)
    return ''


def is_role_manually_editable(user: User) -> bool:
    """Права вручную можно менять только при «— без сегмента»."""
    return detect_user_membership(user) == ''


def role_for_membership(membership: str) -> str | None:
    """Какие права диктует группа. None — группа не задаёт права (без сегмента)."""
    if membership == ROLE_ADMIN:
        return ROLE_ADMIN
    if membership == ROLE_STAFF:
        return ROLE_STAFF
    if membership in SEGMENT_LABELS:
        return ROLE_USER
    if parse_custom_membership(membership) is not None:
        return ROLE_USER
    return None


def membership_key_for_group(group: Group) -> str | None:
    name = (group.name or '').strip()
    by_name = {label: key for key, label in MEMBERSHIP_CHOICES if key}
    if name in by_name:
        return by_name[name]
    if name and name not in ALL_MANAGED_GROUP_NAMES:
        return custom_membership_key(group.pk)
    return None


def get_members_queryset(group: Group):
    """Участники группы с учётом флагов staff/superuser."""
    name = (group.name or '').strip()
    if name == GROUP_ADMIN:
        return User.objects.filter(Q(groups=group) | Q(is_superuser=True)).distinct()
    if name == GROUP_STAFF:
        return User.objects.filter(
            Q(groups=group) | Q(is_staff=True, is_superuser=False)
        ).distinct()
    return group.user_set.all()


def sync_group_members(group: Group) -> int:
    """Подтягивает в M2M суперпользователей / персонал, если группа стандартная."""
    name = (group.name or '').strip()
    added = 0
    if name == GROUP_ADMIN:
        for user in User.objects.filter(is_superuser=True).exclude(groups=group):
            user.groups.add(group)
            added += 1
    elif name == GROUP_STAFF:
        for user in User.objects.filter(is_staff=True, is_superuser=False).exclude(groups=group):
            user.groups.add(group)
            added += 1
    return added


def get_or_create_named_group(name: str) -> Group:
    group, _ = Group.objects.get_or_create(name=name)
    return group


def _clear_managed_groups(user: User) -> None:
    for group_name in ALL_MANAGED_GROUP_NAMES:
        group = Group.objects.filter(name=group_name).first()
        if group:
            user.groups.remove(group)


def _clear_custom_groups(user: User) -> None:
    for group in list(user.groups.exclude(name__in=ALL_MANAGED_GROUP_NAMES)):
        user.groups.remove(group)


def _clear_all_membership_groups(user: User) -> None:
    _clear_managed_groups(user)
    _clear_custom_groups(user)


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
    """Назначает пользователю упрощённую роль доступа и синхронизирует группу."""
    if role not in ROLE_LABELS:
        raise ValueError('Неизвестная роль')

    ensure_default_groups()

    if actor is not None and actor.pk == user.pk and role != ROLE_ADMIN:
        if user.is_superuser or user_is_blocked(user) or role == ROLE_BLOCKED:
            raise PermissionError('Нельзя менять права своему аккаунту таким образом')

    current_membership = detect_user_membership(user)
    current_segment = detect_user_segment(user)
    user.user_permissions.clear()

    if role == ROLE_BLOCKED:
        _clear_all_membership_groups(user)
        user.is_superuser = False
        user.is_staff = False
        user.is_active = False
        user.save(update_fields=['is_superuser', 'is_staff', 'is_active'])
        _set_user_blocked(user, True)
        return

    _set_user_blocked(user, False)

    if role == ROLE_ADMIN:
        _clear_all_membership_groups(user)
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.save(update_fields=['is_superuser', 'is_staff', 'is_active'])
        user.groups.add(get_or_create_named_group(GROUP_ADMIN))
        return

    if role == ROLE_STAFF:
        _clear_all_membership_groups(user)
        user.is_superuser = False
        user.is_staff = True
        user.is_active = True
        user.save(update_fields=['is_superuser', 'is_staff', 'is_active'])
        staff_group = get_or_create_named_group(GROUP_STAFF)
        apply_permissions_for_role(staff_group, ROLE_STAFF)
        user.groups.add(staff_group)
        return

    # Пользователь сайта
    for group_name in ACCESS_GROUP_NAMES.values():
        group = Group.objects.filter(name=group_name).first()
        if group:
            user.groups.remove(group)

    user.is_superuser = False
    user.is_staff = False
    user.is_active = True
    user.save(update_fields=['is_superuser', 'is_staff', 'is_active'])

    if parse_custom_membership(current_membership):
        return
    if current_membership in (ROLE_ADMIN, ROLE_STAFF) or not current_segment:
        _clear_custom_groups(user)
        set_user_segment(user, SEGMENT_BASE)
    elif current_segment:
        set_user_segment(user, current_segment)


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


@transaction.atomic
def set_user_membership(user: User, membership: str, *, actor: User | None = None) -> None:
    """Назначает группу и сразу выставляет соответствующие права."""
    if not is_known_membership(membership):
        raise ValueError('Неизвестная группа')

    ensure_default_groups()

    custom_id = parse_custom_membership(membership)
    if custom_id is not None:
        if actor is not None and actor.pk == user.pk and user.is_superuser:
            raise PermissionError('Нельзя понизить права своему аккаунту')
        group = Group.objects.filter(pk=custom_id).first()
        if not group:
            raise ValueError('Группа не найдена')
        _clear_all_membership_groups(user)
        user.user_permissions.clear()
        user.is_superuser = False
        user.is_staff = False
        user.is_active = True
        user.save(update_fields=['is_superuser', 'is_staff', 'is_active'])
        _set_user_blocked(user, False)
        user.groups.add(group)
        return

    if membership == ROLE_ADMIN:
        set_user_access_role(user, ROLE_ADMIN, actor=actor)
        return

    if membership == ROLE_STAFF:
        set_user_access_role(user, ROLE_STAFF, actor=actor)
        return

    if membership in SEGMENT_LABELS:
        if actor is not None and actor.pk == user.pk and user.is_superuser:
            raise PermissionError('Нельзя понизить права своему аккаунту')

        _clear_all_membership_groups(user)
        user.user_permissions.clear()
        user.is_superuser = False
        user.is_staff = False
        user.is_active = True
        user.save(update_fields=['is_superuser', 'is_staff', 'is_active'])
        _set_user_blocked(user, False)
        set_user_segment(user, membership)
        return

    # — без сегмента
    if actor is not None and actor.pk == user.pk and user.is_superuser:
        raise PermissionError('Нельзя понизить права своему аккаунту')

    _clear_all_membership_groups(user)
    user.user_permissions.clear()
    user.is_superuser = False
    user.is_staff = False
    user.is_active = True
    user.save(update_fields=['is_superuser', 'is_staff', 'is_active'])
    _set_user_blocked(user, False)


def move_user_to_group(user: User, target_group: Group, *, actor: User | None = None) -> None:
    """Переносит пользователя в группу (стандартную или созданную)."""
    key = membership_key_for_group(target_group)
    if key:
        set_user_membership(user, key, actor=actor)
        return
    user.groups.add(target_group)


def format_user_groups_summary(user: User) -> str:
    role = ROLE_LABELS.get(detect_user_access_role(user), 'Пользователь')
    membership = membership_label(detect_user_membership(user))
    if membership and membership not in ('— без сегмента',) and membership not in ROLE_LABELS.values():
        return f'{role} · {membership}'
    return membership if membership != '— без сегмента' else role
