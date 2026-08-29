"""Периоды, агрегация и данные для графика статистики сайта."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, time, timedelta
from urllib.parse import urlencode

from django.db import DatabaseError
from django.db.models import Count
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date

from core.models import ProductPageView, SiteVisit

logger = logging.getLogger(__name__)

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


def _geo_label(row: dict) -> str:
    parts = [
        row.get('geo_country') or '',
        row.get('geo_region') or '',
        row.get('geo_city') or '',
    ]
    parts = [part.strip() for part in parts if part and part.strip()]
    return ', '.join(parts)


def resolve_stats_period(request, *, default='today'):
    today = timezone.localdate()
    changelist_url = reverse('admin:analytics_sitestatistics_changelist')

    if (request.GET.get('reset') or '').strip():
        start, end = stats_period_range(today, 'today')
        query = urlencode({
            'period': 'today',
            'date_from': start.isoformat(),
            'date_to': end.isoformat(),
        })
        return None, redirect(f'{changelist_url}?{query}')

    raw_period = (request.GET.get('period') or '').strip()
    raw_from = (request.GET.get('date_from') or '').strip()
    raw_to = (request.GET.get('date_to') or '').strip()

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


def _bucket_key_from_dt(value, granularity: str, tz):
    if value is None:
        return None
    local = timezone.localtime(value, tz)
    if granularity == 'hour':
        return (local.year, local.month, local.day, local.hour)
    if granularity == 'day':
        return (local.year, local.month, local.day)
    return (local.year, local.month)


def _format_chart_label(bucket_key, granularity: str) -> str:
    year, month = bucket_key[0], bucket_key[1]
    if granularity == 'hour':
        return f'{bucket_key[3]:02d}:00'
    if granularity == 'day':
        return f'{bucket_key[2]:02d}.{month:02d}'
    return f'{_MONTH_LABELS[month - 1]} {year}'


def _iter_chart_bucket_keys(date_from: date, date_to: date, granularity: str, tz):
    if granularity == 'hour':
        day_start, _ = _aware_day_bounds(date_from, tz)
        for hour in range(24):
            local = timezone.localtime(day_start + timedelta(hours=hour), tz)
            yield (local.year, local.month, local.day, local.hour)
        return

    if granularity == 'day':
        cursor = date_from
        while cursor <= date_to:
            yield (cursor.year, cursor.month, cursor.day)
            cursor += timedelta(days=1)
        return

    cursor = date(date_from.year, date_from.month, 1)
    end_marker = date(date_to.year, date_to.month, 1)
    while cursor <= end_marker:
        yield (cursor.year, cursor.month)
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)


def build_chart_data(date_from, date_to, site_qs, product_qs, tz):
    granularity = _chart_granularity(date_from, date_to)

    visits_map = {}
    for visited_at in site_qs.values_list('visited_at', flat=True):
        key = _bucket_key_from_dt(visited_at, granularity, tz)
        if key is not None:
            visits_map[key] = visits_map.get(key, 0) + 1

    views_map = {}
    for viewed_at in product_qs.values_list('viewed_at', flat=True):
        key = _bucket_key_from_dt(viewed_at, granularity, tz)
        if key is not None:
            views_map[key] = views_map.get(key, 0) + 1

    labels = []
    visits = []
    views = []
    for bucket_key in _iter_chart_bucket_keys(date_from, date_to, granularity, tz):
        labels.append(_format_chart_label(bucket_key, granularity))
        visits.append(visits_map.get(bucket_key, 0))
        views.append(views_map.get(bucket_key, 0))

    return {
        'labels': labels,
        'visits': visits,
        'views': views,
        'granularity': granularity,
    }


def _fetch_visit_rows(site_qs):
    fields = (
        'visited_at',
        'path',
        'ip_address',
        'device',
        'geo_country',
        'geo_region',
        'geo_city',
    )
    try:
        rows = list(site_qs.order_by('-visited_at').values(*fields)[:500])
    except DatabaseError:
        logger.exception('Не удалось загрузить заходы с IP/устройством')
        rows = list(site_qs.order_by('-visited_at').values('visited_at', 'path')[:500])
        for row in rows:
            row['ip_address'] = None
            row['device'] = ''
            row['geo_country'] = ''
            row['geo_region'] = ''
            row['geo_city'] = ''

    return [
        {
            **row,
            'device_kind': _device_kind(row.get('device') or ''),
            'geo_label': _geo_label(row),
        }
        for row in rows
    ]


def build_site_stats_context(request, *, default_period='today'):
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
    visit_rows = _fetch_visit_rows(site_qs)
    total_site_visits = site_qs.count()

    return {
        'date_from': date_from.isoformat(),
        'date_to': date_to.isoformat(),
        'period': period,
        'period_choices': stats_period_choices(today),
        'stats_timezone_label': 'Владивосток (UTC+10)',
        'total_site_visits': total_site_visits,
        'total_product_views': product_qs.count(),
        'rows': rows,
        'has_rows': bool(rows),
        'chart_data_json': json.dumps(chart, ensure_ascii=False),
        'chart_granularity': chart['granularity'],
        'visit_rows': visit_rows,
        'has_visits': bool(visit_rows),
        'visits_truncated': total_site_visits > len(visit_rows),
    }, None
