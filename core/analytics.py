"""Учёт заходов на сайт и просмотров карточек товаров."""

from __future__ import annotations

import hashlib
import logging
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)

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


def should_track_site_visit(request) -> bool:
    if request.method != 'GET':
        return False
    path = (request.path or '/').split('?', 1)[0]
    if path.startswith('/admin/'):
        return False
    if path.startswith('/static/') or path.startswith('/media/'):
        return False
    if path in {'/favicon.ico', '/robots.txt'}:
        return False
    if (request.headers.get('X-Requested-With') or '').lower() == 'xmlhttprequest':
        return False
    if _is_bot(request):
        return False
    if _is_staff_user(request):
        return False
    return True


def record_site_visit(request) -> None:
    """Каждый заход на витрину — отдельная запись (без объединения по IP/сессии)."""
    try:
        if not should_track_site_visit(request):
            return

        from core.models import SiteVisit

        path = (request.path or '/')[:300]
        SiteVisit.objects.create(path=path)
    except Exception:
        logger.exception('Не удалось записать заход на сайт')


def visitor_key_for_request(request) -> str:
    if getattr(request, 'user', None) is not None and request.user.is_authenticated:
        return f'u:{request.user.pk}'
    if not request.session.session_key:
        request.session.save()
    if request.session.session_key:
        return f's:{request.session.session_key}'
    # Крайний случай без сессии
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
