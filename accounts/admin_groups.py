from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.models import Group, User
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import escape, format_html, mark_safe

from .forms_roles import SimpleGroupForm
from .models import SITE_ACTIVITY_DAYS
from .roles import (
    ALL_MANAGED_GROUP_NAMES,
    ROLE_CHOICES,
    ROLE_LABELS,
    apply_permissions_for_role,
    detect_group_role,
    ensure_default_groups,
    get_members_queryset,
    membership_key_for_group,
    move_user_to_group,
    set_user_membership,
    sync_group_members,
)


def _header(text):
    return {
        'text': text,
        'sortable': False,
        'sorted': False,
        'ascending': False,
        'sort_priority': 0,
        'url_primary': '',
        'url_remove': '',
        'url_toggle': '',
        'class_attrib': mark_safe(''),
    }


def _td(content):
    return mark_safe(f'<td>{content}</td>')


class SimpleGroupAdmin(DjangoGroupAdmin):
    form = SimpleGroupForm
    list_display = ('name', 'role_col', 'users_count')
    search_fields = ('name',)
    ordering = ('name',)
    filter_horizontal = ()
    fieldsets = (
        (None, {'fields': ('name', 'role')}),
    )

    class Media:
        css = {
            'all': (
                'admin/css/inbox_expandable.css',
                'admin/css/user_expandable.css',
                'admin/css/group_members.css',
                'admin/css/user_roles.css',
            )
        }
        js = (
            'admin/js/inbox_expandable.js',
            'admin/js/user_expandable.js',
            'admin/js/user_roles.js',
            'admin/js/group_members.js',
        )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related('permissions')
            .annotate(_users_count=Count('user', distinct=True))
        )

    def changelist_view(self, request, extra_context=None):
        ensure_default_groups()
        for group in Group.objects.filter(name__in=ALL_MANAGED_GROUP_NAMES):
            sync_group_members(group)
        return super().changelist_view(request, extra_context)

    def add_view(self, request, form_url='', extra_context=None):
        ensure_default_groups()
        return super().add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        ensure_default_groups()
        group = get_object_or_404(Group, pk=object_id)
        sync_group_members(group)

        role = detect_group_role(group)
        membership_key = membership_key_for_group(group) or ''
        expandable_rows, members_count = self._members_expandable_rows(
            request, group, membership_key
        )

        context = {
            **self.admin_site.each_context(request),
            **(extra_context or {}),
            'title': f'ГРУППА {group.name.upper()}',
            'opts': self.model._meta,
            'original': group,
            'group_obj': group,
            'group_role': role,
            'group_role_choices': ROLE_CHOICES,
            'members_count': members_count,
            'membership_key': membership_key,
            'add_user_url': reverse('admin:auth_group_add_member', args=[group.pk]),
            'users_autocomplete_url': reverse('admin:auth_group_users_search', args=[group.pk]),
            'expandable_rows': expandable_rows,
            'result_headers': [
                _header(''),
                _header('имя пользователя'),
                _header('имя'),
                _header('телефон'),
                _header('заявок за год'),
                _header('сумма за год'),
                _header('активность'),
                _header('последний вход'),
                _header('права'),
                _header('группа'),
            ],
            'num_sorted_fields': 0,
            'result_hidden_fields': [],
            'site_activity_days': SITE_ACTIVITY_DAYS,
            'has_view_permission': self.has_view_permission(request, group),
            'has_add_permission': self.has_add_permission(request),
            'has_change_permission': self.has_change_permission(request, group),
            'has_delete_permission': self.has_delete_permission(request, group),
            'media': self.media,
        }
        return TemplateResponse(request, 'admin/auth/group/change_form.html', context)

    def _members_expandable_rows(self, request, group, membership_key):
        user_admin = self.admin_site._registry.get(User)
        if user_admin is None:
            return [], 0

        member_ids = list(get_members_queryset(group).values_list('pk', flat=True))
        qs = (
            user_admin.get_queryset(request)
            .filter(pk__in=member_ids)
            .order_by('username')
        )
        rows = []
        for user in qs:
            membership_html = user_admin.membership_col(user)
            # Пометить select для авто-удаления строки при смене группы
            membership_html = mark_safe(
                str(membership_html).replace(
                    'class="user-membership-select"',
                    f'class="user-membership-select group-page-membership" '
                    f'data-current-group-key="{escape(membership_key)}"',
                    1,
                )
            )
            username = format_html(
                '<a href="{}">{}</a>',
                reverse('admin:auth_user_change', args=[user.pk]),
                user.username,
            )
            cells = [
                _td(user_admin.expand_toggle(user)),
                _td(username),
                _td(escape(user.first_name or '')),
                _td(user_admin.phone_col(user)),
                _td(user_admin.orders_year_count(user)),
                _td(user_admin.orders_year_sum(user)),
                _td(user_admin.site_activity_col(user)),
                _td(user_admin.last_site_visit_col(user)),
                _td(user_admin.access_role_col(user)),
                _td(membership_html),
            ]
            rows.append({
                'result': cells,
                'obj': user,
                'row_status': user_admin.get_row_status(user),
                'details_html': user_admin.row_details_html(user),
            })
        return rows, len(rows)

    def _toolbar_save(self, request, group):
        if not self._can_manage(request):
            return JsonResponse({'ok': False, 'error': 'Forbidden'}, status=403)

        new_name = (request.POST.get('name') or '').strip()
        role = (request.POST.get('role') or '').strip()
        if not new_name:
            return JsonResponse({'ok': False, 'error': 'Укажите имя группы'}, status=400)
        if role not in ROLE_LABELS:
            return JsonResponse({'ok': False, 'error': 'Неизвестные права'}, status=400)

        if new_name != group.name:
            if Group.objects.filter(name=new_name).exclude(pk=group.pk).exists():
                return JsonResponse({'ok': False, 'error': 'Группа с таким именем уже есть'}, status=400)
            group.name = new_name
            group.save(update_fields=['name'])

        apply_permissions_for_role(group, role)
        return JsonResponse({
            'ok': True,
            'name': group.name,
            'role': role,
            'title': f'ГРУППА {group.name.upper()}',
        })

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
            path(
                '<path:object_id>/toolbar-save/',
                self.admin_site.admin_view(self.toolbar_save_view),
                name='auth_group_toolbar_save',
            ),
        ]
        return custom + urls

    def toolbar_save_view(self, request, object_id):
        if request.method != 'POST':
            return JsonResponse({'ok': False, 'error': 'POST only'}, status=405)
        group = get_object_or_404(Group, pk=object_id)
        return self._toolbar_save(request, group)

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
        if not get_members_queryset(group).filter(pk=user.pk).exists():
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
        member_ids = list(get_members_queryset(group).values_list('pk', flat=True))
        qs = User.objects.exclude(pk__in=member_ids).order_by('username')
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
        return get_members_queryset(obj).count()
