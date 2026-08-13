from django.contrib import admin

from .models import Favorite, Order, OrderItem, StainHelpRequest


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'product_name', 'price', 'quantity')
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
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

    @admin.display(description='Сумма')
    def total_display(self, obj):
        return f'{obj.total:.0f} руб'


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    search_fields = ('user__username', 'product__name')


@admin.register(StainHelpRequest)
class StainHelpRequestAdmin(admin.ModelAdmin):
    list_display = (
        'created_at',
        'full_name',
        'phone',
        'contact_method',
        'short_problem',
        'email_sent',
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

    @admin.display(description='Что не отмывается')
    def short_problem(self, obj):
        text = (obj.problem or '').strip().replace('\n', ' ')
        return text if len(text) <= 80 else f'{text[:77]}…'

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
