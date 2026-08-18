from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html

from .models import DeliveryAddress, Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0


class DeliveryAddressInline(admin.TabularInline):
    model = DeliveryAddress
    extra = 0


@admin.action(description='Выдать полный доступ в админку')
def grant_admin_access(modeladmin, request, queryset):
    updated = queryset.update(is_staff=True, is_superuser=True)
    messages.success(request, f'Полный доступ в админку выдан: {updated}')


@admin.action(description='Забрать доступ в админку')
def revoke_admin_access(modeladmin, request, queryset):
    # Суперпользователя себе случайно не снимаем
    qs = queryset.exclude(pk=request.user.pk)
    updated = qs.update(is_staff=False, is_superuser=False)
    skipped = queryset.count() - qs.count()
    if updated:
        messages.success(request, f'Доступ в админку отключён: {updated}')
    if skipped:
        messages.warning(request, 'Свой аккаунт через это действие не меняется.')


class UserAdmin(DjangoUserAdmin):
    inlines = [ProfileInline, DeliveryAddressInline]
    list_display = (
        'username',
        'email',
        'first_name',
        'phone_col',
        'admin_access_col',
        'is_active',
        'last_login',
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'profile__phone')
    actions = (grant_admin_access, revoke_admin_access)
    filter_horizontal = ('groups', 'user_permissions')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Личные данные', {'fields': ('first_name', 'last_name', 'email')}),
        (
            'Доступ в админку',
            {
                'description': (
                    'Для полноценной работы в админке включите «Статус суперпользователя» — '
                    'тогда человек увидит все разделы, как главный администратор. '
                    'Только «Статус персонала» без суперпользователя открывает вход, '
                    'но меню останется пустым.'
                ),
                'fields': ('is_active', 'is_superuser', 'is_staff', 'groups', 'user_permissions'),
            },
        ),
        ('Системное', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'username',
                    'password1',
                    'password2',
                    'email',
                    'first_name',
                    'is_superuser',
                ),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if obj.is_superuser:
            obj.is_staff = True
        super().save_model(request, obj, form, change)

    @admin.display(description='Телефон', ordering='profile__phone')
    def phone_col(self, obj):
        profile = getattr(obj, 'profile', None)
        return (profile.phone or '—') if profile else '—'

    @admin.display(description='Админка', ordering='is_superuser')
    def admin_access_col(self, obj):
        if obj.is_superuser:
            return format_html('<span style="font-weight:600;">{}</span>', 'полный доступ')
        if obj.is_staff:
            return format_html('<span style="color:#c60;">{}</span>', 'только вход')
        return format_html('<span style="color:#888;">{}</span>', 'нет')


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone')
    search_fields = ('user__username', 'user__email', 'phone')


@admin.register(DeliveryAddress)
class DeliveryAddressAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'address', 'is_default', 'created_at')
    list_filter = ('is_default',)
    search_fields = ('name', 'address', 'user__username')
