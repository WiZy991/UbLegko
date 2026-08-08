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

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
# По умолчанию включено для HTTPS; отключить явно: SESSION_COOKIE_SECURE=0
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', '1') == '1'
CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', '1') == '1'
X_FRAME_OPTIONS = 'DENY'
