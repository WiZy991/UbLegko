from django.contrib import admin
from django.contrib.auth.models import Group
from django.db.models import Q

from .roles import (
    ALL_MANAGED_GROUP_NAMES,
    ROLE_ADMIN,
    ROLE_STAFF,
    ROLE_USER,
)


class AccessRoleFilter(admin.SimpleListFilter):
    title = 'Права'
    parameter_name = 'access_role'

    def lookups(self, request, model_admin):
        return (
            (ROLE_ADMIN, 'Администратор'),
            (ROLE_STAFF, 'Персонал'),
            (ROLE_USER, 'Пользователь'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == ROLE_ADMIN:
            return queryset.filter(is_superuser=True)
        if value == ROLE_STAFF:
            return queryset.filter(is_staff=True, is_superuser=False)
        if value == ROLE_USER:
            return queryset.filter(is_staff=False, is_superuser=False)
        return queryset


class ManagedGroupFilter(admin.SimpleListFilter):
    title = 'группы'
    parameter_name = 'managed_group'

    def lookups(self, request, model_admin):
        items = [(name, name) for name in ALL_MANAGED_GROUP_NAMES]
        items.append(('__none__', '— без сегмента'))
        # Прочие группы, если есть
        extras = (
            Group.objects.exclude(name__in=ALL_MANAGED_GROUP_NAMES)
            .order_by('name')
            .values_list('name', flat=True)
        )
        for name in extras:
            items.append((name, name))
        return items

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset
        if value == '__none__':
            return queryset.exclude(
                groups__name__in=ALL_MANAGED_GROUP_NAMES
            ).distinct()
        return queryset.filter(groups__name=value).distinct()
