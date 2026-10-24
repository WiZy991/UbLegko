from django.contrib import admin

from .models import City, SiteSettings


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'note', 'region', 'is_default', 'is_active', 'sort_order')
    list_editable = ('is_default', 'is_active', 'sort_order')
    list_filter = ('is_active', 'region', 'is_default')
    search_fields = ('name', 'region', 'note')


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Бренд', {'fields': ('brand_name', 'slogan', 'tagline', 'company_name')}),
        ('Контакты', {'fields': ('phone', 'email', 'order_email', 'city', 'address', 'full_address')}),
        ('Прочее', {'fields': ('working_hours', 'inn', 'ogrn', 'max_channel_url', 'stain_help_auto_modal')}),
        (
            'Защита от роботов (DDoS)',
            {
                'fields': ('ddos_rate_limit_hits', 'ddos_rate_window_seconds'),
                'description': (
                    'Если с одного IP приходит столько хитов за указанное число секунд — '
                    'IP блокируется на 1 час. Можно менять и на странице «Статистика по сайту».'
                ),
            },
        ),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
