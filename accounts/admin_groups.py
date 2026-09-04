from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin

from .forms_roles import SimpleGroupForm
from .roles import ROLE_LABELS, detect_group_role, ensure_default_groups


class SimpleGroupAdmin(DjangoGroupAdmin):
    form = SimpleGroupForm
    list_display = ('name', 'role_col', 'users_count')
    search_fields = ('name',)
    ordering = ('name',)
    filter_horizontal = ('permissions',)

    fieldsets = (
        (
            None,
            {
                'description': (
                    'Сначала выберите упрощённые права. '
                    'Для сегментов клиентов (VIP / постоянные / клиенты) ставьте «Пользователь».'
                ),
                'fields': ('name', 'role'),
            },
        ),
        (
            'Дополнительно',
            {
                'classes': ('collapse',),
                'description': (
                    'Здесь можно вручную включить или выключить отдельные разрешения Django. '
                    'Если нужна только роль — откройте блок и включите «Заполнить по шаблону», '
                    'либо оставьте шаблон при создании группы.'
                ),
                'fields': ('use_role_template', 'permissions'),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('permissions')

    def changelist_view(self, request, extra_context=None):
        ensure_default_groups()
        return super().changelist_view(request, extra_context)

    def add_view(self, request, form_url='', extra_context=None):
        ensure_default_groups()
        return super().add_view(request, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        # Права группы — через form.save_m2m / apply_permissions
        form.save_m2m()
        for formset in formsets:
            self.save_formset(request, form, formset, change=change)

    @admin.display(description='Права')
    def role_col(self, obj):
        return ROLE_LABELS.get(detect_group_role(obj), 'Пользователь')

    @admin.display(description='Участников')
    def users_count(self, obj):
        return obj.user_set.count()
