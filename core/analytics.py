"""Учёт заходов на сайт и просмотров карточек товаров."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.core.validators import validate_ipv46_address
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from core.geoip import lookup_ip_geo

logger = logging.getLogger(__name__)

FREEZE_MINUTES = 5
RATE_WINDOW_SECONDS = 10
RATE_LIMIT_HITS = 15
BLOCK_DURATION = timedelta(hours=1)

_BOT_MARKERS = (
    'bot',
    'spider',
    'crawl',
    'slurp',
    'facebookexternalhit',
    'preview',
    'wget',
    'curl',
    'python-requests',
    'httpclient',
    'monitoring',
)


def _is_bot(request) -> bool:
    ua = (request.META.get('HTTP_USER_AGENT') or '').lower()
    if not ua:
        return True
    return any(marker in ua for marker in _BOT_MARKERS)


def _is_staff_user(request) -> bool:
    user = getattr(request, 'user', None)
    return bool(
        user is not None
        and user.is_authenticated
        and (user.is_staff or user.is_superuser)
    )


def _should_rate_limit_request(request) -> bool:
    path = (request.path or '/').split('?', 1)[0]
    if path.startswith('/static/') or path.startswith('/media/'):
        return False
    if path in {'/favicon.ico', '/robots.txt'}:
        return False
    return True


def should_track_site_visit(request) -> bool:
    if request.method != 'GET':
        return False
    path = (request.path or '/').split('?', 1)[0]
    if path.startswith('/admin/'):
        return False
    if not _should_rate_limit_request(request):
        return False
    if (request.headers.get('X-Requested-With') or '').lower() == 'xmlhttprequest':
        return False
    if _is_bot(request):
        return False
    if _is_staff_user(request):
        return False
    return True


def client_ip_for_request(request) -> str | None:
    candidates = []
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        candidates.append(xff.split(',')[0].strip())
    xri = request.META.get('HTTP_X_REAL_IP')
    if xri:
        candidates.append(xri.strip())
    candidates.append((request.META.get('REMOTE_ADDR') or '').strip())

    for raw in candidates:
        if not raw:
            continue
        try:
            validate_ipv46_address(raw)
        except ValidationError:
            continue
        return raw[:45]
    return None


def is_ip_blocked(ip: str | None) -> bool:
    if not ip:
        return False
    from core.models import BlockedIP

    return BlockedIP.objects.filter(
        ip_address=ip,
        blocked_until__gt=timezone.now(),
    ).exists()


def active_blocked_ips() -> set[str]:
    from core.models import BlockedIP

    now = timezone.now()
    return set(
        BlockedIP.objects.filter(blocked_until__gt=now).values_list('ip_address', flat=True)
    )


def unblock_ip(ip: str) -> bool:
    """Снимает блокировку IP и очищает счётчик rate-limit."""
    if not ip:
        return False
    from core.models import BlockedIP, IPRateHit

    deleted, _ = BlockedIP.objects.filter(ip_address=ip).delete()
    IPRateHit.objects.filter(ip_address=ip).delete()
    if deleted:
        logger.info('IP %s разблокирован вручную', ip)
    return deleted > 0


def _block_ip(ip: str) -> None:
    from core.models import BlockedIP

    BlockedIP.objects.update_or_create(
        ip_address=ip,
        defaults={'blocked_until': timezone.now() + BLOCK_DURATION},
    )
    logger.warning('IP %s заблокирован на 1 час (DDoS-порог)', ip)


def _register_rate_hit_and_maybe_block(ip: str) -> bool:
    """Регистрирует хит. Возвращает True, если IP нужно заблокировать."""
    from core.models import IPRateHit

    now = timezone.now()
    cutoff = now - timedelta(seconds=RATE_WINDOW_SECONDS)
    IPRateHit.objects.filter(hit_at__lt=now - timedelta(minutes=5)).delete()
    IPRateHit.objects.create(ip_address=ip)
    hits = IPRateHit.objects.filter(ip_address=ip, hit_at__gte=cutoff).count()
    if hits >= RATE_LIMIT_HITS:
        _block_ip(ip)
        return True
    return False


def device_label_for_user_agent(ua: str) -> str:
    ua_lower = (ua or '').lower()
    if not ua_lower:
        return 'Неизвестно'

    if 'iphone' in ua_lower:
        platform = 'iPhone'
    elif 'ipad' in ua_lower:
        platform = 'iPad'
    elif 'android' in ua_lower:
        platform = 'Android'
    elif 'mobile' in ua_lower:
        platform = 'Телефон'
    elif 'windows' in ua_lower:
        platform = 'Windows'
    elif 'mac os' in ua_lower or 'macintosh' in ua_lower:
        platform = 'macOS'
    elif 'linux' in ua_lower:
        platform = 'Linux'
    else:
        platform = 'ПК'

    if 'yabrowser' in ua_lower:
        browser = 'Яндекс'
    elif 'edg/' in ua_lower or 'edge/' in ua_lower:
        browser = 'Edge'
    elif 'opr/' in ua_lower or 'opera' in ua_lower:
        browser = 'Opera'
    elif 'firefox' in ua_lower:
        browser = 'Firefox'
    elif 'samsungbrowser' in ua_lower:
        browser = 'Samsung Internet'
    elif 'chrome' in ua_lower and 'chromium' not in ua_lower:
        browser = 'Chrome'
    elif 'safari' in ua_lower and 'chrome' not in ua_lower:
        browser = 'Safari'
    else:
        browser = 'Браузер'

    return f'{browser} · {platform}'


def device_label_for_request(request) -> str:
    return device_label_for_user_agent(request.META.get('HTTP_USER_AGENT') or '')


def record_site_visit(request) -> None:
    """Один логический заход: один IP в окне 5 минут от первого хита."""
    try:
        if not should_track_site_visit(request):
            return

        from core.models import SiteVisit

        ip = client_ip_for_request(request)
        if ip and is_ip_blocked(ip):
            return

        now = timezone.now()
        freeze_since = now - timedelta(minutes=FREEZE_MINUTES)
        path = (request.path or '/')[:300]
        key = visitor_key_for_request(request)
        device = device_label_for_request(request)

        with transaction.atomic():
            open_visit = None
            if ip:
                open_visit = (
                    SiteVisit.objects.select_for_update()
                    .filter(ip_address=ip, visited_at__gt=freeze_since)
                    .order_by('-visited_at')
                    .first()
                )
            if open_visit is None:
                open_visit = (
                    SiteVisit.objects.select_for_update()
                    .filter(visitor_key=key, visited_at__gt=freeze_since)
                    .order_by('-visited_at')
                    .first()
                )

            if open_visit is not None:
                SiteVisit.objects.filter(pk=open_visit.pk).update(
                    hit_count=F('hit_count') + 1,
                    last_hit_at=now,
                    path=path,
                )
                return

            geo = lookup_ip_geo(ip) if ip else {}
            SiteVisit.objects.create(
                path=path,
                visitor_key=key,
                ip_address=ip,
                device=device,
                hit_count=1,
                **geo,
            )
    except Exception:
        logger.exception('Не удалось записать заход на сайт')


def visitor_key_for_request(request) -> str:
    if getattr(request, 'user', None) is not None and request.user.is_authenticated:
        return f'u:{request.user.pk}'
    if not request.session.session_key:
        request.session.save()
    if request.session.session_key:
        return f's:{request.session.session_key}'
    raw = '|'.join(
        [
            request.META.get('REMOTE_ADDR') or '',
            request.META.get('HTTP_USER_AGENT') or '',
        ]
    )
    return 'h:' + hashlib.sha256(raw.encode('utf-8', errors='ignore')).hexdigest()[:40]


def record_product_view(request, product) -> None:
    """Пишет просмотр карточки. Ошибки не ломают страницу товара."""
    try:
        if product is None or not getattr(product, 'pk', None):
            return
        if _is_bot(request):
            return
        if _is_staff_user(request):
            return

        from core.models import ProductPageView

        key = visitor_key_for_request(request)
        ProductPageView.objects.create(product_id=product.pk, visitor_key=key)
    except Exception:
        logger.exception('Не удалось записать просмотр product_id=%s', getattr(product, 'pk', None))


SEARCH_STATS_DAYS = 7
SEARCH_QUERY_MAX_LEN = 200


def normalize_search_query(raw: str) -> str:
    text = ' '.join((raw or '').split())
    return text.casefold()[:SEARCH_QUERY_MAX_LEN]


def prune_old_search_queries() -> int:
    """Удаляет только записи старше 7 дней."""
    from core.models import SearchQueryLog

    cutoff = timezone.now() - timedelta(days=SEARCH_STATS_DAYS)
    deleted, _ = SearchQueryLog.objects.filter(created_at__lt=cutoff).delete()
    return deleted


def record_search_query(request, raw: str) -> None:
    """Пишет поисковый запрос с витрины. Ошибки не ломают поиск."""
    try:
        query = ' '.join((raw or '').split())[:SEARCH_QUERY_MAX_LEN]
        if not query:
            return
        if _is_bot(request):
            return
        if _is_staff_user(request):
            return

        from core.models import SearchQueryLog

        prune_old_search_queries()
        SearchQueryLog.objects.create(
            query=query,
            query_norm=normalize_search_query(query),
        )
    except Exception:
        logger.exception('Не удалось записать поисковый запрос')
