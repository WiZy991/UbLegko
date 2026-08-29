"""Периоды, агрегация и данные для графика статистики сайта."""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from urllib.parse import urlencode

from django.db.models import Count
from django.db.models.functions import TruncDate, TruncHour, TruncMonth
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date

from core.models import ProductPageView, SiteVisit

STATS_FILTER_SESSION_KEY = 'admin_site_statistics_filter'

STATS_PERIODS = (
    ('today', 'Сегодня', 1),
    ('week', 'Неделя', 7),
    ('month', 'Месяц', 30),
    ('quarter', 'Квартал', 90),
    ('halfyear', 'Полгода', 182),
    ('year', 'Год', 365),
)
STATS_PERIOD_DAYS = {key: days for key, _label, days in STATS_PERIODS}

_MONTH_LABELS = (
    'янв', 'фев', 'мар', 'апр', 'май', 'июн',
    'июл', 'авг', 'сен', 'окт', 'ноя', 'дек',
)

_MOBILE_DEVICE_MARKERS = ('iPhone', 'iPad', 'Android', 'Телефон')


def _device_kind(device: str) -> str:
    text = device or ''
    if any(marker in text for marker in _MOBILE_DEVICE_MARKERS):
        return 'mobile'
    return 'desktop'


def stats_period_range(today, key):
    days = STATS_PERIOD_DAYS.get(key)
    if not days:
        return None
    return today - timedelta(days=days - 1), today


def stats_period_choices(today):
    items = []
    for key, label, _days in STATS_PERIODS:
        start, end = stats_period_range(today, key)
        items.append({
            'key': key,
            'label': label,
            'date_from': start.isoformat(),
            'date_to': end.isoformat(),
        })
    return items


def stats_matching_period(today, date_from, date_to):
    for key, _label, _days in STATS_PERIODS:
        start, end = stats_period_range(today, key)
        if start == date_from and end == date_to:
            return key
    return ''


def stats_filter_redirect(params):
    url = reverse('admin:analytics_sitestatistics_changelist')
    query = urlencode({k: v for k, v in params.items() if v})
    return redirect(f'{url}?{query}' if query else url)


def resolve_stats_period(request, *, default='month'):
    today = timezone.localdate()
    changelist_url = reverse('admin:analytics_sitestatistics_changelist')

    if (request.GET.get('reset') or '').strip():
        request.session.pop(STATS_FILTER_SESSION_KEY, None)
        return None, redirect(changelist_url)

    raw_period = (request.GET.get('period') or '').strip()
    raw_from = (request.GET.get('date_from') or '').strip()
    raw_to = (request.GET.get('date_to') or '').strip()
    has_query = bool(raw_period or raw_from or raw_to)

    if not has_query:
        saved = request.session.get(STATS_FILTER_SESSION_KEY) or {}
        if saved.get('date_from') and saved.get('date_to'):
            return None, stats_filter_redirect({
                'period': saved.get('period') or '',
                'date_from': saved['date_from'],
                'date_to': saved['date_to'],
            })

    date_from = None
    date_to = None
    if raw_period in STATS_PERIOD_DAYS:
        date_from, date_to = stats_period_range(today, raw_period)
    else:
        date_from = parse_date(raw_from) if raw_from else None
        date_to = parse_date(raw_to) if raw_to else None

    if date_from is None or date_to is None:
        date_from, date_to = stats_period_range(today, default)

    if date_from > date_to:
        date_from, date_to = date_to, date_from

    period = stats_matching_period(today, date_from, date_to)
    request.session[STATS_FILTER_SESSION_KEY] = {
        'period': period,
        'date_from': date_from.isoformat(),
        'date_to': date_to.isoformat(),
    }
    return (date_from, date_to, period, today), None


def _chart_granularity(date_from: date, date_to: date) -> str:
    span = (date_to - date_from).days + 1
    if span <= 1:
        return 'hour'
    if span <= 92:
        return 'day'
    return 'month'


def _aware_day_bounds(day: date, tz):
    start = timezone.make_aware(datetime.combine(day, time.min), tz)
    end = timezone.make_aware(datetime.combine(day, time.max), tz)
    return start, end


def _format_chart_label(bucket, granularity: str) -> str:
    local = timezone.localtime(bucket)
    if granularity == 'hour':
        return local.strftime('%H:%M')
    if granularity == 'day':
        return local.strftime('%d.%m')
    return f'{_MONTH_LABELS[local.month - 1]} {local.year}'


def _iter_chart_buckets(date_from: date, date_to: date, granularity: str, tz):
    if granularity == 'hour':
        day_start, _ = _aware_day_bounds(date_from, tz)
        for hour in range(24):
            yield day_start + timedelta(hours=hour)
        return

    if granularity == 'day':
        cursor = date_from
        while cursor <= date_to:
            yield timezone.make_aware(datetime.combine(cursor, time.min), tz)
            cursor += timedelta(days=1)
        return

    cursor = date(date_from.year, date_from.month, 1)
    end_marker = date(date_to.year, date_to.month, 1)
    while cursor <= end_marker:
        yield timezone.make_aware(datetime.combine(cursor, time.min), tz)
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)


def _bucket_key(bucket, granularity: str):
    local = timezone.localtime(bucket)
    if granularity == 'hour':
        return (local.year, local.month, local.day, local.hour)
    if granularity == 'day':
        return (local.year, local.month, local.day)
    return (local.year, local.month)


def build_chart_data(date_from, date_to, site_qs, product_qs, tz):
    granularity = _chart_granularity(date_from, date_to)
    trunc_map = {
        'hour': TruncHour,
        'day': TruncDate,
        'month': TruncMonth,
    }
    trunc = trunc_map[granularity]

    visits_map = {
        _bucket_key(row['bucket'], granularity): row['visits']
        for row in site_qs.annotate(bucket=trunc('visited_at', tzinfo=tz))
        .values('bucket')
        .annotate(visits=Count('id'))
    }
    views_map = {
        _bucket_key(row['bucket'], granularity): row['views']
        for row in product_qs.annotate(bucket=trunc('viewed_at', tzinfo=tz))
        .values('bucket')
        .annotate(views=Count('id'))
    }

    labels = []
    visits = []
    views = []
    for bucket in _iter_chart_buckets(date_from, date_to, granularity, tz):
        key = _bucket_key(bucket, granularity)
        labels.append(_format_chart_label(bucket, granularity))
        visits.append(visits_map.get(key, 0))
        views.append(views_map.get(key, 0))

    return {
        'labels': labels,
        'visits': visits,
        'views': views,
        'granularity': granularity,
    }


def build_site_stats_context(request, *, default_period='month'):
    resolved, redirect_response = resolve_stats_period(request, default=default_period)
    if redirect_response is not None:
        return None, redirect_response

    date_from, date_to, period, today = resolved
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(date_from, time.min), tz)
    end = timezone.make_aware(datetime.combine(date_to, time.max), tz)

    site_qs = SiteVisit.objects.filter(visited_at__gte=start, visited_at__lte=end)
    product_qs = ProductPageView.objects.filter(viewed_at__gte=start, viewed_at__lte=end)

    rows = list(
        product_qs.values(
            'product_id',
            'product__name',
            'product__sku',
            'product__slug',
        )
        .annotate(views=Count('id'))
        .order_by('-views', 'product__name')
    )

    chart = build_chart_data(date_from, date_to, site_qs, product_qs, tz)

    visit_rows = [
        {
            **row,
            'device_kind': _device_kind(row.get('device') or ''),
        }
        for row in site_qs.order_by('-visited_at').values(
            'visited_at',
            'ip_address',
            'device',
            'path',
        )[:500]
    ]

    return {
        'date_from': date_from.isoformat(),
        'date_to': date_to.isoformat(),
        'period': period,
        'period_choices': stats_period_choices(today),
        'stats_timezone_label': 'Владивосток (UTC+10)',
        'total_site_visits': site_qs.count(),
        'total_product_views': product_qs.count(),
        'rows': rows,
        'has_rows': bool(rows),
        'chart_data_json': json.dumps(chart, ensure_ascii=False),
        'chart_granularity': chart['granularity'],
        'visit_rows': visit_rows,
        'has_visits': bool(visit_rows),
        'visits_truncated': site_qs.count() > len(visit_rows),
    }, None
