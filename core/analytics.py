"""Учёт просмотров карточек товаров."""

from __future__ import annotations

import hashlib
import logging
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)

# Не писать повторный просмотр того же товара тем же человеком чаще чем раз в N минут
DEDUP_MINUTES = 30

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
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated and (user.is_staff or user.is_superuser):
            return

        from core.models import ProductPageView

        key = visitor_key_for_request(request)
        since = timezone.now() - timedelta(minutes=DEDUP_MINUTES)
        exists = ProductPageView.objects.filter(
            product_id=product.pk,
            visitor_key=key,
            viewed_at__gte=since,
        ).exists()
        if exists:
            return

        ProductPageView.objects.create(product_id=product.pk, visitor_key=key)
    except Exception:
        logger.exception('Не удалось записать просмотр product_id=%s', getattr(product, 'pk', None))
