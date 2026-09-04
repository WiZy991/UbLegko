from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.models import Group, User
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import path, reverse

from .forms_roles import SimpleGroupForm
from .roles import (
    ALL_MANAGED_GROUP_NAMES,
    MEMBERSHIP_CHOICES,
    ROLE_LABELS,
    detect_group_role,
    ensure_default_groups,
    move_user_to_group,
    set_user_membership,
)


class SimpleGroupAdmin(DjangoGroupAdmin):
    form = SimpleGroupForm
    change_form_template = 'admin/auth/group/change_form.html'
    list_display = ('name', 'role_col', 'users_count')
    search_fields = ('name',)
    ordering = ('name',)
    filter_horizontal = ('permissions',)

    fieldsets = (
        (
            None,
            {
                'description': (
                    'Название группы и упрощённые права. '
                    'Участники группы — в таблице ниже.'
                ),
                'fields': ('name', 'role'),
            },
        ),
        (
            'Дополнительно',
            {
                'classes': ('collapse',),
                'description': (
                    'Ручная настройка отдельных разрешений Django. '
                    'Включите «Заполнить по шаблону», чтобы перезаписать список шаблоном роли.'
                ),
                'fields': ('use_role_template', 'permissions'),
            },
        ),
    )

    class Media:
        css = {'all': ('admin/css/group_members.css',)}
        js = ('admin/js/group_members.js',)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('permissions')

    def changelist_view(self, request, extra_context=None):
        ensure_default_groups()
        return super().changelist_view(request, extra_context)

    def add_view(self, request, form_url='', extra_context=None):
        ensure_default_groups()
        return super().add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        ensure_default_groups()
        extra_context = extra_context or {}
        group = get_object_or_404(Group, pk=object_id)
        members = group.user_set.select_related('profile').order_by('username')
        other_groups = Group.objects.exclude(pk=group.pk).order_by('name')
        extra_context.update({
            'group_members': members,
            'other_groups': other_groups,
            'add_user_url': reverse('admin:auth_group_add_member', args=[group.pk]),
            'users_autocomplete_url': reverse('admin:auth_group_users_search', args=[group.pk]),
        })
        return super().change_view(request, object_id, form_url, extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                '<path:object_id>/members/add/',
                self.admin_site.admin_view(self.add_member_view),
                name='auth_group_add_member',
            ),
            path(
                '<path:object_id>/members/<int:user_id>/remove/',
                self.admin_site.admin_view(self.remove_member_view),
                name='auth_group_remove_member',
            ),
            path(
                '<path:object_id>/members/<int:user_id>/move/',
                self.admin_site.admin_view(self.move_member_view),
                name='auth_group_move_member',
            ),
            path(
                '<path:object_id>/members/search/',
                self.admin_site.admin_view(self.users_search_view),
                name='auth_group_users_search',
            ),
        ]
        return custom + urls

    def _can_manage(self, request):
        return request.user.is_superuser or request.user.has_perm('auth.change_group')

    def add_member_view(self, request, object_id):
        if request.method != 'POST':
            return JsonResponse({'ok': False, 'error': 'POST only'}, status=405)
        if not self._can_manage(request):
            return JsonResponse({'ok': False, 'error': 'Forbidden'}, status=403)

        group = get_object_or_404(Group, pk=object_id)
        try:
            user_id = int(request.POST.get('user_id') or '')
        except (TypeError, ValueError):
            return JsonResponse({'ok': False, 'error': 'Выберите пользователя'}, status=400)

        user = User.objects.filter(pk=user_id).first()
        if not user:
            return JsonResponse({'ok': False, 'error': 'Пользователь не найден'}, status=404)

        try:
            move_user_to_group(user, group, actor=request.user)
        except PermissionError as exc:
            return JsonResponse({'ok': False, 'error': str(exc)}, status=400)

        return JsonResponse({
            'ok': True,
            'redirect': reverse('admin:auth_group_change', args=[group.pk]),
        })

    def remove_member_view(self, request, object_id, user_id):
        if request.method != 'POST':
            return JsonResponse({'ok': False, 'error': 'POST only'}, status=405)
        if not self._can_manage(request):
            return JsonResponse({'ok': False, 'error': 'Forbidden'}, status=403)

        group = get_object_or_404(Group, pk=object_id)
        user = get_object_or_404(User, pk=user_id)
        if not group.user_set.filter(pk=user.pk).exists():
            return JsonResponse({'ok': False, 'error': 'Пользователь не в группе'}, status=400)

        if group.name in ALL_MANAGED_GROUP_NAMES:
            try:
                set_user_membership(user, '', actor=request.user)
            except PermissionError as exc:
                return JsonResponse({'ok': False, 'error': str(exc)}, status=400)
        else:
            group.user_set.remove(user)

        return JsonResponse({'ok': True})

    def move_member_view(self, request, object_id, user_id):
        if request.method != 'POST':
            return JsonResponse({'ok': False, 'error': 'POST only'}, status=405)
        if not self._can_manage(request):
            return JsonResponse({'ok': False, 'error': 'Forbidden'}, status=403)

        get_object_or_404(Group, pk=object_id)
        user = get_object_or_404(User, pk=user_id)
        try:
            target = Group.objects.get(pk=int(request.POST.get('target_group_id') or ''))
        except (TypeError, ValueError, Group.DoesNotExist):
            return JsonResponse({'ok': False, 'error': 'Выберите группу'}, status=400)

        try:
            move_user_to_group(user, target, actor=request.user)
        except PermissionError as exc:
            return JsonResponse({'ok': False, 'error': str(exc)}, status=400)

        return JsonResponse({
            'ok': True,
            'redirect': reverse('admin:auth_group_change', args=[target.pk]),
        })

    def users_search_view(self, request, object_id):
        if not self._can_manage(request):
            return JsonResponse({'ok': False, 'error': 'Forbidden'}, status=403)

        group = get_object_or_404(Group, pk=object_id)
        q = (request.GET.get('q') or '').strip()
        qs = User.objects.exclude(groups=group).order_by('username')
        if q:
            qs = qs.filter(
                Q(username__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(email__icontains=q)
            )
        qs = qs[:20]
        return JsonResponse({
            'ok': True,
            'results': [
                {
                    'id': u.pk,
                    'text': f'{u.username}' + (f' ({u.get_full_name()})' if u.get_full_name() else ''),
                }
                for u in qs
            ],
        })

    def save_related(self, request, form, formsets, change):
        form.save_m2m()
        for formset in formsets:
            self.save_formset(request, form, formset, change=change)

    @admin.display(description='Права')
    def role_col(self, obj):
        return ROLE_LABELS.get(detect_group_role(obj), 'Пользователь')

    @admin.display(description='Участников')
    def users_count(self, obj):
        return obj.user_set.count()
