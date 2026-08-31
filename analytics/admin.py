from datetime import timedelta

from django.contrib import admin, messages
from django.db.models import Count, Max
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from core.analytics import SEARCH_STATS_DAYS, prune_old_search_queries, unblock_ip

from .models import SearchStatistics, SiteStatistics
from .stats import build_site_stats_context


@admin.register(SiteStatistics)
class SiteStatisticsAdmin(admin.ModelAdmin):
    change_list_template = 'admin/analytics/sitestatistics/stats.html'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_staff

    def changelist_view(self, request, extra_context=None):
        if request.method == 'POST' and request.POST.get('action') == 'unblock_ip':
            if not request.user.is_staff:
                return self.admin_site.login(request)

            ip = (request.POST.get('ip_address') or '').strip()
            if ip:
                if unblock_ip(ip):
                    messages.success(request, f'IP {ip} разблокирован.')
                else:
                    messages.warning(request, f'IP {ip} не был в блокировке.')
            else:
                messages.error(request, 'Не указан IP для разблокировки.')

            redirect_url = reverse('admin:analytics_sitestatistics_changelist')
            query = request.GET.urlencode()
            if query:
                redirect_url = f'{redirect_url}?{query}'
            return redirect(redirect_url)

        context, redirect_response = build_site_stats_context(request)
        if redirect_response is not None:
            return redirect_response

        context = {
            **self.admin_site.each_context(request),
            'title': 'Статистика по сайту',
            'opts': self.model._meta,
            'cl': None,
            **context,
        }
        if extra_context:
            context.update(extra_context)
        return render(request, self.change_list_template, context)


@admin.register(SearchStatistics)
class SearchStatisticsAdmin(admin.ModelAdmin):
    change_list_template = 'admin/analytics/searchstatistics/stats.html'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_staff

    def changelist_view(self, request, extra_context=None):
        prune_old_search_queries()
        cutoff = timezone.now() - timedelta(days=SEARCH_STATS_DAYS)
        qs = SearchStatistics.objects.filter(created_at__gte=cutoff)

        sort = (request.GET.get('sort') or 'date').strip()
        if sort not in {'date', 'hits'}:
            sort = 'date'
        order_by = ('-last_at', '-hits') if sort == 'date' else ('-hits', '-last_at')

        grouped = list(
            qs.values('query_norm')
            .annotate(hits=Count('id'), last_at=Max('created_at'))
            .order_by(*order_by)
        )
        latest_label = {}
        for item in qs.order_by('query_norm', '-created_at').values('query_norm', 'query'):
            latest_label.setdefault(item['query_norm'], item['query'])

        rows = [
            {
                'query': latest_label.get(row['query_norm']) or row['query_norm'],
                'hits': row['hits'],
                'last_at': row['last_at'],
            }
            for row in grouped
        ]

        context = {
            **self.admin_site.each_context(request),
            'title': 'Статистика по поиску',
            'opts': self.model._meta,
            'cl': None,
            'rows': rows,
            'has_rows': bool(rows),
            'total_hits': qs.count(),
            'total_queries': len(rows),
            'keep_days': SEARCH_STATS_DAYS,
            'sort': sort,
            'sort_choices': [
                {'key': 'date', 'label': 'По дате (новые сверху)'},
                {'key': 'hits', 'label': 'По количеству (частые сверху)'},
            ],
        }
        return render(request, self.change_list_template, context)
