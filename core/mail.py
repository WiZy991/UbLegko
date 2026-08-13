"""Общая отправка писем магазина (заявки и запросы)."""

from __future__ import annotations

import logging
import textwrap
from html import escape

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)

# SMTP: строка в DATA не должна быть длиннее ~998 символов (RFC 5321).
_EMAIL_LINE_WIDTH = 900


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


def prepare_email_body(body: str, width: int = _EMAIL_LINE_WIDTH) -> str:
    """Нормализует переносы и режет слишком длинные строки для SMTP."""
    text = (body or '').replace('\r\n', '\n').replace('\r', '\n').strip('\n')
    if not text:
        return ''

    out: list[str] = []
    for paragraph in text.split('\n'):
        if not paragraph:
            out.append('')
            continue
        if len(paragraph) <= width:
            out.append(paragraph)
            continue
        wrapped = textwrap.wrap(
            paragraph,
            width=width,
            break_long_words=True,
            break_on_hyphens=False,
            replace_whitespace=False,
            drop_whitespace=False,
        )
        out.extend(wrapped or [paragraph[:width]])
    return '\n'.join(out) + '\n'


def body_to_html(body: str) -> str:
    """Простой HTML-вариант письма — так Mail.ru реже теряет текст."""
    safe = escape(prepare_email_body(body)).replace('\n', '<br>\n')
    return (
        '<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;'
        'font-size:14px;line-height:1.45;color:#111">'
        f'{safe}'
        '</body></html>'
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

    safe_body = prepare_email_body(body)
    # Тема тоже не должна быть гигантской
    safe_subject = ' '.join((subject or '').split())
    if len(safe_subject) > 180:
        safe_subject = safe_subject[:177] + '...'

    email = EmailMultiAlternatives(
        subject=safe_subject,
        body=safe_body,
        from_email=from_email,
        to=[to_email],
        reply_to=reply_to or None,
    )
    email.encoding = 'utf-8'
    email.attach_alternative(body_to_html(safe_body), 'text/html')

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

        logger.info(
            '%s: отправлено на %s (From=%s, subject=%r, body_len=%s)',
            log_label,
            to_email,
            from_email,
            safe_subject,
            len(safe_body),
        )
        return True
    except Exception:
        logger.exception('%s: ошибка отправки на %s (From=%s)', log_label, to_email, from_email)
        return False
