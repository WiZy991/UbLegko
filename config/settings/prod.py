import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403

DEBUG = False

_secret = os.environ.get('DJANGO_SECRET_KEY', '').strip()
if not _secret or _secret.startswith('django-insecure-'):
    raise ImproperlyConfigured(
        'Задайте надёжный DJANGO_SECRET_KEY в окружении для продакшена.'
    )
SECRET_KEY = _secret

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS if h.strip()]
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured('Задайте ALLOWED_HOSTS (через запятую) для продакшена.')


def _expand_allowed_hosts(hosts: list[str]) -> list[str]:
    """Добавляет punycode/unicode-варианты для кириллических доменов (.рф и т.п.)."""
    expanded: list[str] = []
    for host in hosts:
        expanded.append(host)
        try:
            puny = host.encode('idna').decode('ascii')
            if puny and puny not in expanded:
                expanded.append(puny)
        except (UnicodeError, ValueError):
            pass
        try:
            uni = host.encode('ascii').decode('idna')
            if uni and uni not in expanded:
                expanded.append(uni)
        except (UnicodeError, ValueError, UnicodeDecodeError):
            pass
    return expanded


ALLOWED_HOSTS = _expand_allowed_hosts(ALLOWED_HOSTS)

# На проде SITE_URL обязателен для корректного canonical/OG
if not SITE_URL:  # noqa: F405
    _host = ALLOWED_HOSTS[0]
    if _host and _host != '*':
        SITE_URL = f'https://{_host}'  # noqa: F405

_csrf_origins = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(',') if o.strip()]

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
# По умолчанию включено для HTTPS; отключить явно: SESSION_COOKIE_SECURE=0
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', '1') == '1'
CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', '1') == '1'
X_FRAME_OPTIONS = 'DENY'

_backend = (EMAIL_BACKEND or '').lower()
if 'console' in _backend or 'dummy' in _backend or 'locmem' in _backend:
    import logging

    logging.getLogger(__name__).error(
        'EMAIL_BACKEND=%s — заявки не будут приходить на почту. '
        'Задайте SMTP в .env (см. deploy/env.example / .env.example).',
        EMAIL_BACKEND,
    )
