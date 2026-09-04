from decimal import Decimal
import json

from django.contrib import admin, messages
from django.contrib.admin.templatetags.admin_list import (
    ResultList,
    items_for_result,
    result_headers,
    result_hidden_fields,
)
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Prefetch, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import escape, format_html, mark_safe

from cart.models import Favorite, Order, _vladivostok_year
from catalog.models import ProductReview

from .models import SITE_ACTIVITY_DAYS, DeliveryAddress, Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0
    readonly_fields = ('last_site_visit_at',)


class DeliveryAddressInline(admin.TabularInline):
    model = DeliveryAddress
    extra = 0


@admin.action(description='Выдать полный доступ в админку')
def grant_admin_access(modeladmin, request, queryset):
    updated = queryset.update(is_staff=True, is_superuser=True)
    messages.success(request, f'Полный доступ в админку выдан: {updated}')


@admin.action(description='Забрать доступ в админку')
def revoke_admin_access(modeladmin, request, queryset):
    qs = queryset.exclude(pk=request.user.pk)
    updated = qs.update(is_staff=False, is_superuser=False)
    skipped = queryset.count() - qs.count()
    if updated:
        messages.success(request, f'Доступ в админку отключён: {updated}')
    if skipped:
        messages.warning(request, 'Свой аккаунт через это действие не меняется.')


def _format_local_datetime(value):
    if not value:
        return '—'
    return timezone.localtime(value).strftime('%d.%m.%Y %H:%M')


def _money(value) -> str:
    try:
        amount = Decimal(value or 0)
    except Exception:
        amount = Decimal('0')
    return f'{amount:.0f} руб'


class UserAdmin(DjangoUserAdmin):
    change_list_template = 'admin/auth/user/change_list.html'
    inlines = [ProfileInline, DeliveryAddressInline]
    list_display = (
        'expand_toggle',
        'username',
        'first_name',
        'phone_col',
        'orders_year_count',
        'orders_year_sum',
        'site_activity_col',
        'last_site_visit_col',
        'admin_access_col',
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'profile__phone')
    actions = (grant_admin_access, revoke_admin_access)
    filter_horizontal = ('groups', 'user_permissions')
    ordering = (
        F('profile__last_site_visit_at').desc(nulls_last=True),
        F('last_login').desc(nulls_last=True),
        '-date_joined',
    )

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

    def get_queryset(self, request):
        year = _vladivostok_year()
        qs = super().get_queryset(request)
        return (
            qs.select_related('profile')
            .prefetch_related(
                'delivery_addresses',
                Prefetch(
                    'favorites',
                    queryset=Favorite.objects.select_related('product').order_by('-created_at'),
                ),
                Prefetch(
                    'product_reviews',
                    queryset=ProductReview.objects.select_related('product').order_by('-created_at'),
                ),
                Prefetch(
                    'orders',
                    queryset=Order.objects.prefetch_related('items').order_by('-created_at'),
                ),
            )
            .annotate(
                _orders_year_count=Count(
                    'orders',
                    filter=Q(orders__number_year=year),
                    distinct=True,
                ),
                _orders_year_sum=Coalesce(
                    Sum(
                        ExpressionWrapper(
                            F('orders__items__price') * F('orders__items__quantity'),
                            output_field=DecimalField(max_digits=14, decimal_places=2),
                        ),
                        filter=Q(orders__number_year=year),
                    ),
                    Value(Decimal('0.00')),
                ),
            )
        )

    def save_model(self, request, obj, form, change):
        if obj.is_superuser:
            obj.is_staff = True
        super().save_model(request, obj, form, change)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                '<path:object_id>/review/<int:review_id>/save/',
                self.admin_site.admin_view(self.save_review_view),
                name='auth_user_review_save',
            ),
            path(
                '<path:object_id>/review/<int:review_id>/delete/',
                self.admin_site.admin_view(self.delete_review_view),
                name='auth_user_review_delete',
            ),
        ]
        return custom + urls

    def save_review_view(self, request, object_id, review_id):
        if request.method != 'POST':
            return JsonResponse({'ok': False, 'error': 'POST only'}, status=405)
        if not request.user.has_perm('catalog.change_productreview'):
            return JsonResponse({'ok': False, 'error': 'Forbidden'}, status=403)

        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except (TypeError, ValueError, json.JSONDecodeError):
            return JsonResponse({'ok': False, 'error': 'Bad JSON'}, status=400)

        review = ProductReview.objects.filter(pk=review_id, user_id=object_id).first()
        if not review:
            return JsonResponse({'ok': False, 'error': 'Not found'}, status=404)

        try:
            rating = int(payload.get('rating'))
        except (TypeError, ValueError):
            return JsonResponse({'ok': False, 'error': 'Некорректная оценка'}, status=400)
        if rating < 1 or rating > 5:
            return JsonResponse({'ok': False, 'error': 'Оценка от 1 до 5'}, status=400)

        comment = str(payload.get('comment') or '').strip()
        if len(comment) > 2000:
            return JsonResponse({'ok': False, 'error': 'Комментарий слишком длинный'}, status=400)

        review.rating = rating
        review.comment = comment
        review.save(update_fields=['rating', 'comment', 'updated_at'])
        return JsonResponse({
            'ok': True,
            'rating': review.rating,
            'comment': review.comment,
            'reviews_count': ProductReview.objects.filter(user_id=object_id).count(),
        })

    def delete_review_view(self, request, object_id, review_id):
        if request.method != 'POST':
            return JsonResponse({'ok': False, 'error': 'POST only'}, status=405)
        if not request.user.has_perm('catalog.delete_productreview'):
            return JsonResponse({'ok': False, 'error': 'Forbidden'}, status=403)

        review = ProductReview.objects.filter(pk=review_id, user_id=object_id).first()
        if not review:
            return JsonResponse({'ok': False, 'error': 'Not found'}, status=404)

        review.delete()
        return JsonResponse({
            'ok': True,
            'reviews_count': ProductReview.objects.filter(user_id=object_id).count(),
        })

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['site_activity_days'] = SITE_ACTIVITY_DAYS
        response = super().changelist_view(request, extra_context=extra_context)
        if not hasattr(response, 'context_data'):
            return response

        cl = response.context_data.get('cl')
        if not cl:
            return response

        rows = []
        if cl.formset:
            for res, form in zip(cl.result_list, cl.formset.forms):
                rows.append({
                    'result': ResultList(form, items_for_result(cl, res, form)),
                    'obj': res,
                    'row_status': self.get_row_status(res),
                    'details_html': self.row_details_html(res),
                })
        else:
            for res in cl.result_list:
                rows.append({
                    'result': ResultList(None, items_for_result(cl, res, None)),
                    'obj': res,
                    'row_status': self.get_row_status(res),
                    'details_html': self.row_details_html(res),
                })

        headers = list(result_headers(cl))
        num_sorted_fields = sum(
            1 for header in headers if header.get('sortable') and header.get('sorted')
        )
        response.context_data.update({
            'expandable_rows': rows,
            'result_headers': headers,
            'num_sorted_fields': num_sorted_fields,
            'result_hidden_fields': list(result_hidden_fields(cl)),
        })
        return response

    def get_row_status(self, obj):
        profile = getattr(obj, 'profile', None)
        if profile and profile.is_site_active:
            return 'active'
        return 'inactive'

    @admin.display(description='')
    def expand_toggle(self, obj):
        return format_html(
            '<button type="button" class="inbox-row-expand" data-inbox-id="{}" '
            'aria-expanded="false" aria-label="Подробнее" title="Подробнее">'
            '<i class="fas fa-chevron-down" aria-hidden="true"></i>'
            '</button>',
            obj.pk,
        )

    @admin.display(description='Телефон', ordering='profile__phone')
    def phone_col(self, obj):
        profile = getattr(obj, 'profile', None)
        return (profile.phone or '—') if profile else '—'

    @admin.display(description='Заявок за год', ordering='_orders_year_count')
    def orders_year_count(self, obj):
        return getattr(obj, '_orders_year_count', 0) or 0

    @admin.display(description='Сумма за год', ordering='_orders_year_sum')
    def orders_year_sum(self, obj):
        return _money(getattr(obj, '_orders_year_sum', 0))

    @admin.display(description='Активность')
    def site_activity_col(self, obj):
        profile = getattr(obj, 'profile', None)
        active = profile.is_site_active if profile else False
        if active:
            return format_html(
                '<span class="user-activity-badge user-activity-badge--on">{}</span>',
                'Активный',
            )
        return format_html(
            '<span class="user-activity-badge user-activity-badge--off">{}</span>',
            'Неактивный',
        )

    @admin.display(description='Последний вход', ordering='profile__last_site_visit_at')
    def last_site_visit_col(self, obj):
        profile = getattr(obj, 'profile', None)
        value = None
        if profile and profile.last_site_visit_at:
            value = profile.last_site_visit_at
        elif obj.last_login:
            value = obj.last_login
        return _format_local_datetime(value)

    @admin.display(description='Админка', ordering='is_superuser')
    def admin_access_col(self, obj):
        if obj.is_superuser:
            return format_html('<span style="font-weight:600;">{}</span>', 'полный доступ')
        if obj.is_staff:
            return format_html('<span style="color:#c60;">{}</span>', 'только вход')
        return format_html('<span style="color:#888;">{}</span>', 'нет')

    def row_details_html(self, obj):
        profile = getattr(obj, 'profile', None)
        phone = (profile.phone or '—') if profile else '—'
        last_visit = None
        if profile and profile.last_site_visit_at:
            last_visit = profile.last_site_visit_at
        elif obj.last_login:
            last_visit = obj.last_login

        addresses = list(obj.delivery_addresses.all())
        favorites = list(obj.favorites.all())
        reviews = list(obj.product_reviews.all())
        orders = list(obj.orders.all())

        blocks = [
            self._detail_block('Email', obj.email or '—'),
            self._detail_block('Телефон', phone),
            self._detail_block('Регистрация', _format_local_datetime(obj.date_joined)),
            self._detail_block('Последний вход на сайт', _format_local_datetime(last_visit)),
            self._detail_block(
                'Активность на сайте',
                'Активный' if (profile and profile.is_site_active) else 'Неактивный',
            ),
            self._detail_block(
                'Аккаунт',
                'подтверждён' if obj.is_active else 'не подтверждён / отключён',
            ),
        ]

        addresses_html = self._addresses_section(addresses)
        favorites_html = self._favorites_section(favorites)
        reviews_html = self._reviews_section(reviews)
        orders_html = self._orders_section(orders)

        return mark_safe(
            '<div class="inbox-row-detail__inner user-row-detail">'
            '<div class="inbox-row-detail__grid">'
            + ''.join(blocks)
            + '</div>'
            + addresses_html
            + favorites_html
            + reviews_html
            + orders_html
            + '</div>'
        )

    def _detail_block(self, label, value, *, wide=False):
        wide_cls = ' inbox-row-detail__block--wide' if wide else ''
        return (
            f'<div class="inbox-row-detail__block{wide_cls}">'
            f'<span class="inbox-row-detail__label">{escape(label)}</span>'
            f'<div class="inbox-row-detail__value">{escape(str(value))}</div>'
            f'</div>'
        )

    def _addresses_section(self, addresses):
        count = len(addresses)
        if count == 0:
            body = '<p class="user-fold__empty">Адресов в профиле нет.</p>'
        else:
            items = []
            for addr in addresses:
                default = ' · по умолчанию' if addr.is_default else ''
                items.append(
                    f'<li><strong>{escape(addr.name)}</strong>{escape(default)}'
                    f'<br>{escape(addr.address)}</li>'
                )
            body = f'<ul class="user-fold__list">{"".join(items)}</ul>'

        if count <= 1:
            return (
                f'<div class="user-fold user-fold--static">'
                f'<div class="user-fold__title">Адреса ({count})</div>'
                f'{body}</div>'
            )
        return (
            f'<details class="user-fold">'
            f'<summary>Адреса ({count})</summary>'
            f'<div class="user-fold__body">{body}</div>'
            f'</details>'
        )

    def _favorites_section(self, favorites):
        count = len(favorites)
        if count == 0:
            body = '<p class="user-fold__empty">В избранном пусто.</p>'
        else:
            items = []
            for fav in favorites:
                product = fav.product
                name = getattr(product, 'name', None) or 'Товар'
                sku = getattr(product, 'sku', None) or ''
                sku_html = f' · арт. {escape(sku)}' if sku else ''
                items.append(
                    f'<li><strong>{escape(name)}</strong>{sku_html}'
                    f'<br><span class="user-fold__muted">добавлено '
                    f'{escape(_format_local_datetime(fav.created_at))}</span></li>'
                )
            body = f'<ul class="user-fold__list">{"".join(items)}</ul>'

        return (
            f'<details class="user-fold">'
            f'<summary>Избранное ({count})</summary>'
            f'<div class="user-fold__body">{body}</div>'
            f'</details>'
        )

    def _reviews_section(self, reviews):
        count = len(reviews)
        if count == 0:
            body = '<p class="user-fold__empty">Оценок и комментариев нет.</p>'
        else:
            items = []
            for review in reviews:
                product_name = getattr(review.product, 'name', None) or 'Товар'
                comment = review.comment or ''
                rating_opts = ''.join(
                    f'<option value="{n}"{" selected" if n == int(review.rating) else ""}>'
                    f'{n}★</option>'
                    for n in range(1, 6)
                )
                save_url = reverse('admin:auth_user_review_save', args=[review.user_id, review.pk])
                delete_url = reverse('admin:auth_user_review_delete', args=[review.user_id, review.pk])
                items.append(
                    f'<li class="user-review-item" data-review-id="{review.pk}">'
                    f'<div class="user-review-item__head">'
                    f'<strong>{escape(product_name)}</strong>'
                    f'<span class="user-fold__muted">'
                    f'{escape(_format_local_datetime(review.created_at))}</span>'
                    f'</div>'
                    f'<label class="user-review-item__label">Оценка'
                    f'<select class="user-review-item__rating" name="rating">{rating_opts}</select>'
                    f'</label>'
                    f'<label class="user-review-item__label">Комментарий'
                    f'<textarea class="user-review-item__comment" rows="3" maxlength="2000">'
                    f'{escape(comment)}</textarea>'
                    f'</label>'
                    f'<div class="user-review-item__actions">'
                    f'<button type="button" class="user-review-btn user-review-btn--save" '
                    f'data-save-url="{escape(save_url)}">Сохранить</button>'
                    f'<button type="button" class="user-review-btn user-review-btn--delete" '
                    f'data-delete-url="{escape(delete_url)}">Удалить</button>'
                    f'<span class="user-review-item__status" hidden></span>'
                    f'</div>'
                    f'</li>'
                )
            body = f'<ul class="user-fold__list user-fold__list--reviews">{"".join(items)}</ul>'

        return (
            f'<details class="user-fold" open>'
            f'<summary class="user-reviews-summary">Комментарии и оценки '
            f'(<span class="user-reviews-count">{count}</span>)</summary>'
            f'<div class="user-fold__body">{body}</div>'
            f'</details>'
        )

    def _orders_section(self, orders):
        current_year = _vladivostok_year()
        by_year: dict[int, list] = {}
        for order in orders:
            year = int(getattr(order, 'number_year', None) or _vladivostok_year(order.created_at))
            by_year.setdefault(year, []).append(order)

        years = sorted(by_year.keys(), reverse=True)
        if not years:
            return (
                '<details class="user-fold">'
                f'<summary>Заказы (0) · <strong>{escape(_money(0))}</strong></summary>'
                '<div class="user-fold__body">'
                '<p class="user-fold__empty">Заявок пока нет.</p>'
                '</div></details>'
            )

        parts = []
        for year in years:
            year_orders = by_year[year]
            count = len(year_orders)
            total = sum((order.total for order in year_orders), start=Decimal('0'))
            body = self._orders_year_body(year_orders)
            total_html = f'<strong>{escape(_money(total))}</strong>'
            if year == current_year:
                title = f'Заказы ({count}) · {total_html}'
                open_attr = ' open'
            else:
                title = f'Заявки за {year} год ({count}) · {total_html}'
                open_attr = ''
            parts.append(
                f'<details class="user-fold"{open_attr}>'
                f'<summary>{title}</summary>'
                f'<div class="user-fold__body">{body}</div>'
                f'</details>'
            )
        return ''.join(parts)

    def _orders_year_body(self, orders):
        if not orders:
            return '<p class="user-fold__empty">Заявок пока нет.</p>'
        items = []
        for order in orders:
            lines = []
            for item in order.items.all():
                lines.append(
                    f'<li>{escape(item.product_name)} × {item.quantity} — '
                    f'{escape(_money(item.line_total))}</li>'
                )
            lines_html = (
                f'<ul class="user-fold__sublist">{"".join(lines)}</ul>'
                if lines
                else '<p class="user-fold__empty">Нет позиций</p>'
            )
            items.append(
                f'<li class="user-fold__order">'
                f'<strong>Заявка №{order.number}</strong> · '
                f'{escape(_format_local_datetime(order.created_at))} · '
                f'<strong>{escape(_money(order.total))}</strong>'
                f'{lines_html}'
                f'</li>'
            )
        return f'<ul class="user-fold__list">{"".join(items)}</ul>'


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'last_site_visit_at')
    search_fields = ('user__username', 'user__email', 'phone')
    readonly_fields = ('last_site_visit_at',)


@admin.register(DeliveryAddress)
class DeliveryAddressAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'address', 'is_default', 'created_at')
    list_filter = ('is_default',)
    search_fields = ('name', 'address', 'user__username')
