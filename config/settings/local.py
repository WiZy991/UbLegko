from .base import *  # noqa: F401,F403
import os

DEBUG = True
ALLOWED_HOSTS = ['*']

# По умолчанию письма в консоль; если в .env задан EMAIL_BACKEND — берём его
if not os.environ.get('EMAIL_BACKEND'):
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
