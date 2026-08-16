from datetime import datetime, time, timedelta

from django.contrib import admin
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date

from .models import City, ProductPageView, SiteSettings


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


@admin.register(ProductPageView)
class ProductPageViewAdmin(admin.ModelAdmin):
    """Раздел Core → Статистика: просмотры карточек за период."""

    change_list_template = 'admin/core/productpageview/stats.html'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_staff

    def changelist_view(self, request, extra_context=None):
        today = timezone.localdate()
        default_from = today - timedelta(days=29)

        raw_from = (request.GET.get('date_from') or '').strip()
        raw_to = (request.GET.get('date_to') or '').strip()

        date_from = parse_date(raw_from) if raw_from else default_from
        date_to = parse_date(raw_to) if raw_to else today
        if date_from is None:
            date_from = default_from
        if date_to is None:
            date_to = today
        if date_from > date_to:
            date_from, date_to = date_to, date_from

        tz = timezone.get_current_timezone()
        start = timezone.make_aware(datetime.combine(date_from, time.min), tz)
        end = timezone.make_aware(datetime.combine(date_to, time.max), tz)

        base_qs = ProductPageView.objects.filter(viewed_at__gte=start, viewed_at__lte=end)

        total_views = base_qs.count()
        total_visitors = base_qs.values('visitor_key').distinct().count()

        rows = list(
            base_qs.values(
                'product_id',
                'product__name',
                'product__sku',
                'product__slug',
            )
            .annotate(
                visitors=Count('visitor_key', distinct=True),
                views=Count('id'),
            )
            .order_by('-visitors', '-views', 'product__name')
        )

        daily = list(
            base_qs.annotate(day=TruncDate('viewed_at'))
            .values('day')
            .annotate(
                visitors=Count('visitor_key', distinct=True),
                views=Count('id'),
            )
            .order_by('day')
        )

        context = {
            **self.admin_site.each_context(request),
            'title': 'Статистика просмотров',
            'opts': self.model._meta,
            'cl': None,
            'date_from': date_from.isoformat(),
            'date_to': date_to.isoformat(),
            'total_views': total_views,
            'total_visitors': total_visitors,
            'rows': rows,
            'daily': daily,
            'has_rows': bool(rows),
        }
        if extra_context:
            context.update(extra_context)
        return render(request, self.change_list_template, context)
