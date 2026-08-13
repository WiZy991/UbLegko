"""Общая отправка писем магазина (заявки и запросы)."""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import EmailMessage

logger = logging.getLogger(__name__)


def is_real_smtp_backend() -> bool:
    backend = (settings.EMAIL_BACKEND or '').lower()
    return (
        'smtp' in backend
        and 'console' not in backend
        and 'dummy' not in backend
        and 'locmem' not in backend
    )


def resolve_shop_to_email() -> str:
    from core.models import SiteSettings

    site = SiteSettings.load()
    return (site.order_email or getattr(settings, 'ORDER_EMAIL_TO', '') or '').strip()


def resolve_from_email() -> str:
    """
    Для Mail.ru/Beget From должен совпадать с SMTP-логином.
    Если логин пуст — берём DEFAULT_FROM_EMAIL.
    """
    return (
        (getattr(settings, 'EMAIL_HOST_USER', '') or '').strip()
        or (getattr(settings, 'DEFAULT_FROM_EMAIL', '') or '').strip()
    )


def send_shop_email(
    *,
    subject: str,
    body: str,
    to_email: str | None = None,
    reply_to: list[str] | None = None,
    log_label: str = 'письмо',
) -> bool:
    """Отправляет письмо на почту магазина. Возвращает True при успешной SMTP-отправке."""
    to_email = (to_email or resolve_shop_to_email()).strip()
    if not to_email:
        logger.error('%s: нет адреса получателя (order_email / ORDER_EMAIL_TO)', log_label)
        return False

    from_email = resolve_from_email()
    if not from_email:
        logger.error('%s: нет EMAIL_HOST_USER / DEFAULT_FROM_EMAIL', log_label)
        return False

    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=from_email,
        to=[to_email],
        reply_to=reply_to or None,
    )
    try:
        if not is_real_smtp_backend():
            email.send(fail_silently=False)
            logger.error(
                '%s: EMAIL_BACKEND=%s — письмо не ушло на почту (нужен SMTP)',
                log_label,
                settings.EMAIL_BACKEND,
            )
            return False

        sent = email.send(fail_silently=False)
        if not sent:
            logger.error('%s: SMTP вернул 0 (письмо на %s не принято)', log_label, to_email)
            return False

        logger.info('%s: отправлено на %s (From=%s)', log_label, to_email, from_email)
        return True
    except Exception:
        logger.exception('%s: ошибка отправки на %s (From=%s)', log_label, to_email, from_email)
        return False
