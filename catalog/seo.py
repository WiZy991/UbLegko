"""SEO-хелперы: абсолютные URL, мета-шаблоны, JSON-LD."""

from __future__ import annotations

import json
import re
from typing import Any

from django.conf import settings

from core.formatting import format_rubles

from .seo_keywords import (
    GEO_CITIES,
    GEO_REGION,
)

# Кластеры запросов по названиям категорий (семантическое ядро)
CATEGORY_SEO_CLUSTERS: dict[str, str] = {
    'Общая уборка': (
        'Моющие средства для пола и универсальные средства для уборки дома. '
        'Чем отмыть жир, пятна, пол, плиту — купить в Уссурийске, Приморский край.'
    ),
    'Химчистка': (
        'Средства для химчистки, пятновыводители. Чем вывести пятна с ковра, дивана, '
        'как отмыть текстиль — купить в Приморском крае.'
    ),
    'Для стирки': (
        'Средства для стирки, отбеливатели. Чем отстирать кровь, жир, пятна с одежды — '
        'купить в Уссурийске, Приморский край.'
    ),
    'Для посудомоечных машин': (
        'Средства и таблетки для посудомоечных машин. '
        'Профессиональная химия — купить в Приморском крае.'
    ),
    'Пищевое производство': (
        'Моющие средства для пищевого производства и HoReCa. '
        'Чем отмыть жир, устранить запах — купить в Уссурийске.'
    ),
    'Освежители и поглотители': (
        'Освежители и поглотители запахов. '
        'Чем устранить запах — купить в Приморском крае.'
    ),
    'Мыло': (
        'Жидкое мыло и средства для рук. '
        'Купить в Уссурийске, Приморский край.'
    ),
    'Антисептики': (
        'Антисептики и дезинфицирующие средства. '
        'Купить в Приморском крае.'
    ),
    'Для машины': (
        'Автохимия, чем отмыть и смыть грязь с автомобиля. '
        'Купить в Уссурийске, Приморский край.'
    ),
    'Масла и смазки': (
        'Технические масла и смазки. Купить в Приморском крае.'
    ),
    'Деревообработка': (
        'Средства для ухода за деревом. Купить в Уссурийске, Приморский край.'
    ),
    'Сопутствующие товары': (
        'Инвентарь для уборки. Моющие средства купить в Приморском крае.'
    ),
    'Услуги': (
        'Услуги магазина профессиональной химии в Уссурийске, Приморский край.'
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
    return f'Моющие средства купить в Уссурийске, {GEO_REGION} | {brand}'


def home_meta_description(site_settings) -> str:
    tagline = (getattr(site_settings, 'tagline', None) or '').strip()
    base = (
        f'Магазин профессиональной химии в Уссурийске, {GEO_REGION}: '
        'чем отмыть жир и пятна, как вывести пятна, чем отстирать, '
        'моющие средства купить с доставкой по краю.'
    )
    if tagline:
        return clip_meta(f'{base} {tagline}')
    return clip_meta(base)


def category_meta_title(category, site_settings) -> str:
    custom = (getattr(category, 'seo_title', None) or '').strip()
    if custom:
        return custom
    brand = brand_label(site_settings)
    return f'{category.name} — купить в Уссурийске, {GEO_REGION} | {brand}'


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
        f'«{category.name}» — профессиональные моющие средства. '
        f'Купить в Уссурийске, {GEO_REGION}. '
        f'Подскажем, чем отмыть и как вывести пятна.'
    )


def product_meta_title(product, site_settings) -> str:
    custom = (getattr(product, 'seo_title', None) or '').strip()
    if custom:
        return custom
    brand = brand_label(site_settings)
    return f'{product.name} — купить в Уссурийске, {GEO_REGION} | {brand}'


def product_meta_description(product) -> str:
    custom = (getattr(product, 'seo_description', None) or '').strip()
    if custom:
        return clip_meta(custom)
    desc = (product.description or '').strip()
    if desc:
        return clip_meta(desc)
    return clip_meta(
        f'{product.name} — купить в Уссурийске, {GEO_REGION}. '
        f'Профессиональная химия, цена {format_rubles(product.price)}. '
        f'Подскажем, чем отмыть и как вывести пятна.'
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
    data['areaServed'] = [
        {
            '@type': 'AdministrativeArea',
            'name': GEO_REGION,
            'addressCountry': 'RU',
        },
        *[
            {
                '@type': 'City',
                'name': city,
                'addressRegion': GEO_REGION,
                'addressCountry': 'RU',
            }
            for city in GEO_CITIES
        ],
    ]
    data['geo'] = {
        '@type': 'GeoCoordinates',
        'addressCountry': 'RU',
        'addressRegion': GEO_REGION,
    }
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
