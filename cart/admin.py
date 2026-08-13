from django.contrib import admin
from django.contrib.admin.templatetags.admin_list import (
    ResultList,
    items_for_result,
    result_headers,
    result_hidden_fields,
)
from django.http import JsonResponse
from django.urls import path
from django.utils.html import escape, format_html, mark_safe

from .models import Favorite, Order, OrderItem, StainHelpRequest


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'product_name', 'price', 'quantity')
    can_delete = False


class InboxExpandableAdminMixin:
    """Раскрывающиеся строки + счётчик новых для changelist."""

    change_list_template = None  # задаётся в наследниках

    def get_inbox_new_count(self):
        raise NotImplementedError

    def get_row_status(self, obj):
        """Значение data-inbox-status: new | processed."""
        raise NotImplementedError

    def row_details_html(self, obj):
        raise NotImplementedError

    @admin.display(description='')
    def expand_toggle(self, obj):
        return format_html(
            '<button type="button" class="inbox-row-expand" data-inbox-id="{}" '
            'aria-expanded="false" aria-label="Подробнее" title="Подробнее">'
            '<i class="fas fa-chevron-down" aria-hidden="true"></i>'
            '</button>',
            obj.pk,
        )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        new_count = self.get_inbox_new_count()
        extra_context['new_count'] = new_count
        plural = self.model._meta.verbose_name_plural
        extra_context['title'] = f'{plural} ({new_count})'
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
            'new_count': new_count,
        })
        return response


@admin.register(Order)
class OrderAdmin(InboxExpandableAdminMixin, admin.ModelAdmin):
    change_list_template = 'admin/cart/order/change_list.html'
    list_display = (
        'expand_toggle',
        'id',
        'full_name',
        'phone',
        'city',
        'delivery_method',
        'email',
        'email_sent',
        'address',
        'address_name',
        'status',
        'created_at',
        'total_display',
    )
    list_filter = ('status', 'delivery_method', 'email_sent', 'created_at')
    search_fields = ('full_name', 'phone', 'email', 'address', 'address_name', 'city')
    list_editable = ('status',)
    readonly_fields = (
        'user',
        'full_name',
        'phone',
        'email',
        'email_sent',
        'delivery_method',
        'address',
        'address_name',
        'city',
        'comment',
        'site_feedback',
        'created_at',
    )
    inlines = [OrderItemInline]
    list_per_page = 50

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('items')

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'inbox-counts/',
                self.admin_site.admin_view(self.inbox_counts_view),
                name='cart_inbox_counts',
            ),
        ]
        return custom + urls

    def inbox_counts_view(self, request):
        return JsonResponse({
            'orders_new': Order.objects.filter(status=Order.Status.NEW).count(),
            'requests_new': StainHelpRequest.objects.filter(is_processed=False).count(),
        })

    def get_inbox_new_count(self):
        return Order.objects.filter(status=Order.Status.NEW).count()

    def get_row_status(self, obj):
        return obj.status if obj.status in ('new', 'processed') else 'new'

    @admin.display(description='Сумма')
    def total_display(self, obj):
        return f'{obj.total:.0f} руб'

    def row_details_html(self, obj):
        items = list(obj.items.all())
        if items:
            items_html = '<ul class="inbox-row-detail__items">' + ''.join(
                f'<li>{escape(item.product_name)} × {item.quantity} — '
                f'{item.line_total:.0f} руб</li>'
                for item in items
            ) + '</ul>'
        else:
            items_html = '<span class="inbox-row-detail__value">Нет позиций</span>'

        comment = (obj.comment or '').strip() or '—'
        feedback = (obj.site_feedback or '').strip() or '—'
        address = (obj.address or '').strip() or '—'
        city = (obj.city or '').strip() or '—'
        delivery = obj.get_delivery_method_display() if obj.delivery_method else '—'

        return mark_safe(
            '<div class="inbox-row-detail__inner">'
            '<div class="inbox-row-detail__grid">'
            f'<div class="inbox-row-detail__block">'
            f'<span class="inbox-row-detail__label">Город</span>'
            f'<div class="inbox-row-detail__value">{escape(city)}</div></div>'
            f'<div class="inbox-row-detail__block">'
            f'<span class="inbox-row-detail__label">Доставка</span>'
            f'<div class="inbox-row-detail__value">{escape(str(delivery))}</div></div>'
            f'<div class="inbox-row-detail__block">'
            f'<span class="inbox-row-detail__label">Адрес</span>'
            f'<div class="inbox-row-detail__value">{escape(address)}</div></div>'
            f'<div class="inbox-row-detail__block inbox-row-detail__block--wide">'
            f'<span class="inbox-row-detail__label">Комментарий</span>'
            f'<div class="inbox-row-detail__value">{escape(comment)}</div></div>'
            f'<div class="inbox-row-detail__block inbox-row-detail__block--wide">'
            f'<span class="inbox-row-detail__label">Замечания по сайту</span>'
            f'<div class="inbox-row-detail__value">{escape(feedback)}</div></div>'
            f'<div class="inbox-row-detail__block inbox-row-detail__block--wide">'
            f'<span class="inbox-row-detail__label">Состав заказа</span>'
            f'{items_html}</div>'
            '</div></div>'
        )


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    search_fields = ('user__username', 'product__name')


@admin.register(StainHelpRequest)
class StainHelpRequestAdmin(InboxExpandableAdminMixin, admin.ModelAdmin):
    change_list_template = 'admin/cart/stainhelprequest/change_list.html'
    list_display = (
        'expand_toggle',
        'created_at',
        'full_name',
        'phone',
        'contact_method',
        'short_problem',
        'email_sent',
        'processed_badge',
        'is_processed',
        'user',
    )
    list_filter = ('is_processed', 'email_sent', 'created_at')
    list_editable = ('is_processed',)
    search_fields = ('full_name', 'phone', 'contact_method', 'problem')
    readonly_fields = (
        'full_name',
        'phone',
        'contact_method',
        'problem',
        'user',
        'email_sent',
        'created_at',
    )
    fields = (
        'created_at',
        'full_name',
        'phone',
        'contact_method',
        'problem',
        'user',
        'email_sent',
        'is_processed',
    )
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    list_per_page = 50

    def get_inbox_new_count(self):
        return StainHelpRequest.objects.filter(is_processed=False).count()

    def get_row_status(self, obj):
        return 'processed' if obj.is_processed else 'new'

    @admin.display(description='Что не отмывается')
    def short_problem(self, obj):
        text = (obj.problem or '').strip().replace('\n', ' ')
        return text if len(text) <= 80 else f'{text[:77]}…'

    @admin.display(description='Статус', ordering='is_processed')
    def processed_badge(self, obj):
        if obj.is_processed:
            return format_html(
                '<span class="status-badge status-badge--done">Обработано</span>'
            )
        return format_html(
            '<span class="status-badge status-badge--new">Новая</span>'
        )

    def row_details_html(self, obj):
        problem = (obj.problem or '').strip() or '—'
        contact = (obj.contact_method or '').strip() or '—'
        phone = (obj.phone or '').strip() or '—'
        name = (obj.full_name or '').strip() or '—'
        return mark_safe(
            '<div class="inbox-row-detail__inner">'
            '<div class="inbox-row-detail__grid">'
            f'<div class="inbox-row-detail__block">'
            f'<span class="inbox-row-detail__label">Имя</span>'
            f'<div class="inbox-row-detail__value">{escape(name)}</div></div>'
            f'<div class="inbox-row-detail__block">'
            f'<span class="inbox-row-detail__label">Телефон</span>'
            f'<div class="inbox-row-detail__value">{escape(phone)}</div></div>'
            f'<div class="inbox-row-detail__block">'
            f'<span class="inbox-row-detail__label">Способ связи</span>'
            f'<div class="inbox-row-detail__value">{escape(contact)}</div></div>'
            f'<div class="inbox-row-detail__block inbox-row-detail__block--wide">'
            f'<span class="inbox-row-detail__label">Сообщение</span>'
            f'<div class="inbox-row-detail__value">{escape(problem)}</div></div>'
            '</div></div>'
        )

    def has_add_permission(self, request):
        return False

    actions = ('resend_email',)

    @admin.action(description='Отправить письмо на почту магазина ещё раз')
    def resend_email(self, request, queryset):
        from django.template.loader import render_to_string

        from core.mail import send_shop_email
        from core.models import SiteSettings

        site = SiteSettings.load()
        ok = 0
        fail = 0
        for obj in queryset:
            subject = f'Запрос №{obj.pk} с сайта {site.brand_name}'
            body = render_to_string(
                'core/email/stain_help.txt',
                {
                    'site': site,
                    'request_obj': obj,
                    'full_name': obj.full_name,
                    'phone': obj.phone,
                    'contact_method': obj.contact_method,
                    'problem': obj.problem,
                },
            )
            if send_shop_email(subject=subject, body=body, log_label=f'Запрос №{obj.pk}'):
                if not obj.email_sent:
                    obj.email_sent = True
                    obj.save(update_fields=['email_sent'])
                ok += 1
            else:
                fail += 1
        if ok:
            self.message_user(request, f'Отправлено писем: {ok}')
        if fail:
            self.message_user(
                request,
                f'Не удалось отправить: {fail}. Проверьте SMTP в .env и логи.',
                level=30,
            )
