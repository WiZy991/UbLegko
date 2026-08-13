from django.contrib import admin

from .models import City, SiteSettings, StainHelpRequest


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
        ('Прочее', {'fields': ('working_hours', 'inn', 'ogrn', 'max_channel_url')}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


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
