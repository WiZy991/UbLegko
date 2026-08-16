"""SEO-хелперы: абсолютные URL, мета-шаблоны, JSON-LD."""

from __future__ import annotations

import json
import re
from typing import Any

from django.conf import settings

# Кластеры запросов по названиям категорий (семантическое ядро)
CATEGORY_SEO_CLUSTERS: dict[str, str] = {
    'Общая уборка': (
        'Моющие средства для пола и универсальные средства для уборки дома. '
        'Профессиональная химия для ежедневной уборки — купить в Уссурийске.'
    ),
    'Химчистка': (
        'Средства для химчистки, пятновыводители и составы для ковров и текстиля. '
        'Профессиональная химия — купить в Уссурийске.'
    ),
    'Для стирки': (
        'Средства для стирки, жидкие порошки и отбеливатели для белья. '
        'Профессиональная химия для стирки — купить в Уссурийске.'
    ),
    'Для посудомоечных машин': (
        'Средства и таблетки для посудомоечных машин. '
        'Профессиональная химия для ПММ — купить в Уссурийске.'
    ),
    'Пищевое производство': (
        'Моющие средства для пищевого производства и профессиональной кухни HoReCa. '
        'Купить в Уссурийске с консультацией.'
    ),
    'Освежители и поглотители': (
        'Освежители воздуха и поглотители запахов для дома и организаций. '
        'Купить в Уссурийске.'
    ),
    'Мыло': (
        'Жидкое мыло и профессиональные средства для рук. '
        'Купить в Уссурийске.'
    ),
    'Антисептики': (
        'Антисептики и дезинфицирующие средства. '
        'Профессиональная химия — купить в Уссурийске.'
    ),
    'Для машины': (
        'Автохимия и средства для мойки автомобиля. '
        'Купить профессиональную химию в Уссурийске.'
    ),
    'Масла и смазки': (
        'Технические масла и смазки. '
        'Купить в Уссурийске.'
    ),
    'Деревообработка': (
        'Средства для ухода за деревом и деревообработки. '
        'Купить в Уссурийске.'
    ),
    'Сопутствующие товары': (
        'Инвентарь для уборки и сопутствующие товары к профессиональной химии. '
        'Купить в Уссурийске.'
    ),
    'Услуги': (
        'Услуги магазина профессиональной химии «Убираемся Легко» в Уссурийске.'
    ),
}

_WS_RE = re.compile(r'\s+')


def site_origin(request=None) -> str:
    configured = (getattr(settings, 'SITE_URL', None) or '').strip().rstrip('/')
    if configured:
        return configured
    if request is not None:
        return f'{request.scheme}://{request.get_host()}'.rstrip('/')
    return ''


def absolute_url(request, path: str | None = None) -> str:
    origin = site_origin(request)
    if path is None:
        path = request.path if request is not None else '/'
    if not path.startswith('/'):
        path = '/' + path
    return f'{origin}{path}'


def clip_meta(text: str, limit: int = 160) -> str:
    text = _WS_RE.sub(' ', (text or '').strip())
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(' ', 1)[0]
    return (cut or text[: limit - 1]).rstrip('.,;:') + '…'


def brand_label(site_settings) -> str:
    return (getattr(site_settings, 'brand_name', None) or 'Убираемся Легко').strip()


def home_meta_title(site_settings) -> str:
    brand = brand_label(site_settings)
    return f'Профессиональные моющие средства купить в Уссурийске | {brand}'


def home_meta_description(site_settings) -> str:
    tagline = (getattr(site_settings, 'tagline', None) or '').strip()
    base = (
        'Магазин профессиональной химии «Убираемся Легко» в Уссурийске: '
        'моющие и чистящие средства для дома и организаций, доставка.'
    )
    if tagline:
        return clip_meta(f'{base} {tagline}')
    return clip_meta(base)


def category_meta_title(category, site_settings) -> str:
    custom = (getattr(category, 'seo_title', None) or '').strip()
    if custom:
        return custom
    brand = brand_label(site_settings)
    return f'{category.name} купить — профессиональные средства | {brand}'


def category_meta_description(category) -> str:
    custom = (getattr(category, 'seo_description', None) or '').strip()
    if custom:
        return clip_meta(custom)
    # seo_text только в meta для роботов — на витрине не показываем
    seo_text = (getattr(category, 'seo_text', None) or '').strip()
    if seo_text:
        return clip_meta(seo_text)
    cluster = CATEGORY_SEO_CLUSTERS.get(category.name)
    if cluster:
        return clip_meta(cluster)
    return clip_meta(
        f'«{category.name}» — профессиональные моющие и чистящие средства. '
        f'Купить в Уссурийске в магазине «Убираемся Легко».'
    )


def product_meta_title(product, site_settings) -> str:
    custom = (getattr(product, 'seo_title', None) or '').strip()
    if custom:
        return custom
    brand = brand_label(site_settings)
    return f'{product.name} — купить в Уссурийске | {brand}'


def product_meta_description(product) -> str:
    custom = (getattr(product, 'seo_description', None) or '').strip()
    if custom:
        return clip_meta(custom)
    desc = (product.description or '').strip()
    if desc:
        return clip_meta(desc)
    return clip_meta(
        f'{product.name} — купить в Уссурийске в магазине профессиональной химии '
        f'«Убираемся Легко». Цена {product.price:.0f} руб.'
    )


def offer_availability(status: str) -> str:
    return {
        'in_stock': 'https://schema.org/InStock',
        'in_transit': 'https://schema.org/PreOrder',
        'out_of_stock': 'https://schema.org/OutOfStock',
        'on_order': 'https://schema.org/PreOrder',
    }.get(status, 'https://schema.org/InStock')


def dumps_ld(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(',', ':'))


def organization_localbusiness_ld(site_settings, request) -> dict:
    origin = site_origin(request)
    phone = (getattr(site_settings, 'phone', None) or '').strip()
    email = (getattr(site_settings, 'email', None) or '').strip()
    address = (getattr(site_settings, 'full_address', None) or getattr(site_settings, 'address', None) or '').strip()
    city = (getattr(site_settings, 'city', None) or 'г. Уссурийск').strip()
    hours = (getattr(site_settings, 'working_hours', None) or '').strip()
    brand = brand_label(site_settings)
    company = (getattr(site_settings, 'company_name', None) or brand).strip()

    data: dict[str, Any] = {
        '@context': 'https://schema.org',
        '@type': ['Organization', 'LocalBusiness', 'Store'],
        'name': brand,
        'legalName': company,
        'url': origin + '/',
        'image': absolute_url(request, '/static/img/og-image.jpg'),
        'address': {
            '@type': 'PostalAddress',
            'addressLocality': city.replace('г.', '').strip(),
            'addressRegion': 'Приморский край',
            'streetAddress': address or city,
            'addressCountry': 'RU',
        },
    }
    if phone:
        data['telephone'] = phone
    if email:
        data['email'] = email
    if hours:
        data['openingHours'] = hours
    inn = (getattr(site_settings, 'inn', None) or '').strip()
    if inn:
        data['taxID'] = inn
    return data


def breadcrumb_ld(items: list[tuple[str, str]], request) -> dict:
    """items: list of (name, path_or_absolute_url)."""
    elements = []
    for i, (name, url) in enumerate(items, start=1):
        if url.startswith('http://') or url.startswith('https://'):
            item_url = url
        else:
            item_url = absolute_url(request, url)
        elements.append(
            {
                '@type': 'ListItem',
                'position': i,
                'name': name,
                'item': item_url,
            }
        )
    return {
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        'itemListElement': elements,
    }


def product_ld(product, request, site_settings) -> dict:
    origin = site_origin(request)
    url = absolute_url(request, product.get_absolute_url())
    image = ''
    if getattr(product, 'image', None):
        try:
            image = absolute_url(request, product.image.url)
        except Exception:
            image = ''
    if not image and getattr(product, 'image_card', None):
        try:
            image = absolute_url(request, product.image_card.url)
        except Exception:
            image = ''

    data: dict[str, Any] = {
        '@context': 'https://schema.org',
        '@type': 'Product',
        'name': product.name,
        'description': clip_meta(product.seo_description or product.description or product.name, 300),
        'sku': (product.sku or str(product.pk)).strip(),
        'url': url,
        'brand': {
            '@type': 'Brand',
            'name': brand_label(site_settings),
        },
        'offers': {
            '@type': 'Offer',
            'url': url,
            'priceCurrency': 'RUB',
            'price': f'{product.price:.2f}',
            'availability': offer_availability(product.status),
            'seller': {
                '@type': 'Organization',
                'name': brand_label(site_settings),
                'url': origin + '/',
            },
        },
    }
    if image:
        data['image'] = [image]
    if product.category_id:
        data['category'] = product.category.name
    if product.reviews_count and product.rating:
        data['aggregateRating'] = {
            '@type': 'AggregateRating',
            'ratingValue': f'{product.rating:.1f}',
            'reviewCount': int(product.reviews_count),
        }
    return data
