from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-zq2s&lxaxn5yn3#eu*%m5to2eo5c=qv9l&fj-=*=7r@15q8ilq',
)

DEBUG = False
ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'catalog',
    'accounts',
    'cart',
]

JAZZMIN_SETTINGS = {
    'site_title': 'Убираемся Легко',
    'site_header': 'Убираемся Легко',
    'site_brand': 'Убираемся Легко',
    'site_logo': None,
    'login_logo': None,
    'site_logo_classes': 'img-circle',
    'site_icon': None,
    'welcome_sign': 'Панель управления сайтом-каталогом',
    'copyright': 'ООО СОЛНЕЧНЫЙ МЕЧ',
    'search_model': ['catalog.Product', 'auth.User', 'cart.Order'],
    'user_avatar': None,
    'topmenu_links': [
        {'name': 'Открыть сайт', 'url': '/', 'new_window': True},
        {'name': 'Каталог', 'url': 'admin:catalog_product_changelist', 'permissions': ['catalog.view_product']},
        {'name': 'Заявки', 'url': 'admin:cart_order_changelist', 'permissions': ['cart.view_order']},
    ],
    'usermenu_links': [
        {'name': 'Открыть сайт', 'url': '/', 'new_window': True},
    ],
    'show_sidebar': True,
    'navigation_expanded': True,
    'hide_apps': [],
    'hide_models': [],
    'order_with_respect_to': [
        'catalog',
        'catalog.Product',
        'catalog.Category',
        'catalog.ProductImage',
        'catalog.ProductRecommendation',
        'cart',
        'cart.Order',
        'cart.Favorite',
        'core',
        'core.SiteSettings',
        'core.City',
        'auth',
    ],
    'icons': {
        'auth': 'fas fa-users-cog',
        'auth.user': 'fas fa-user',
        'auth.Group': 'fas fa-users',
        'catalog.Category': 'fas fa-folder',
        'catalog.Product': 'fas fa-box-open',
        'catalog.ProductImage': 'fas fa-images',
        'catalog.ProductRecommendation': 'fas fa-thumbs-up',
        'cart.Order': 'fas fa-file-invoice',
        'cart.Favorite': 'fas fa-heart',
        'core.City': 'fas fa-map-marker-alt',
        'core.SiteSettings': 'fas fa-cog',
    },
    'default_icon_parents': 'fas fa-chevron-circle-right',
    'default_icon_children': 'fas fa-circle',
    'related_modal_active': True,
    'custom_css': None,
    'custom_js': None,
    'use_google_fonts_cdn': True,
    'show_ui_builder': False,
    'changeform_format': 'horizontal_tabs',
    'changeform_format_overrides': {
        'auth.user': 'collapsible',
        'auth.group': 'vertical_tabs',
        'catalog.product': 'horizontal_tabs',
    },
    'language_chooser': False,
}

JAZZMIN_UI_TWEAKS = {
    'navbar_small_text': False,
    'footer_small_text': False,
    'body_small_text': False,
    'brand_small_text': False,
    'brand_colour': 'navbar-info',
    'accent': 'accent-info',
    'navbar': 'navbar-dark',
    'no_navbar_border': False,
    'navbar_fixed': True,
    'layout_boxed': False,
    'footer_fixed': False,
    'sidebar_fixed': True,
    'sidebar': 'sidebar-dark-info',
    'sidebar_nav_small_text': False,
    'sidebar_disable_expand': False,
    'sidebar_nav_child_indent': True,
    'sidebar_nav_compact_style': False,
    'sidebar_nav_legacy_style': False,
    'sidebar_nav_flat_style': False,
    'theme': 'darkly',
    'default_theme_mode': 'dark',
    'button_classes': {
        'primary': 'btn-info',
        'secondary': 'btn-secondary',
        'info': 'btn-info',
        'warning': 'btn-warning',
        'danger': 'btn-danger',
        'success': 'btn-success',
    },
    'actions_sticky_top': True,
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.site_settings',
                'cart.context_processors.cart',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
]

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Asia/Vladivostok'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:profile'
LOGOUT_REDIRECT_URL = 'catalog:home'

EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend',
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', '1') == '1'
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', '0') == '1'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@ubiraemsya-legko.ru')
ORDER_EMAIL_TO = os.environ.get('ORDER_EMAIL_TO', 'pro-brite_uss@mail.ru')
SERVER_EMAIL = DEFAULT_FROM_EMAIL
