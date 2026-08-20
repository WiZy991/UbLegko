import json

from catalog.seo_keywords import (
    GEO_REGION,
    GEO_REGION_SHORT,
    STAIN_HELP_QUERY_PREFIXES,
    matches_stain_help_query,
    meta_keywords_string,
)

from .models import City, SiteSettings

SESSION_CITY_KEY = 'selected_city_id'


def get_selected_city(request):
    city_id = request.session.get(SESSION_CITY_KEY)
    if city_id:
        city = City.objects.filter(pk=city_id, is_active=True).first()
        if city:
            return city
    city = City.objects.filter(is_default=True, is_active=True).first()
    if city:
        return city
    return City.objects.filter(is_active=True).order_by('sort_order', 'name').first()


def site_settings(request):
    try:
        settings_obj = SiteSettings.load()
    except Exception:  # noqa: BLE001
        settings_obj = SiteSettings(
            brand_name='УБИРАЕМСЯЛЕГКО',
            company_name='ООО СОЛНЕЧНЫЙ МЕЧ',
            phone='8-991-496-18-97',
            email='pro-brite_uss@mail.ru',
        )

    try:
        cities = list(City.objects.filter(is_active=True).order_by('sort_order', 'name'))
        selected_city = get_selected_city(request)
    except Exception:  # noqa: BLE001
        cities = []
        selected_city = None

    return {
        'site_settings': settings_obj,
        'cities': cities,
        'selected_city': selected_city,
        'selected_city_name': (
            selected_city.display_name if selected_city else settings_obj.city
        ),
    }


def _stain_help_search_query(request) -> str:
    path = (request.path or '').rstrip('/')
    if not path.endswith('/search'):
        return ''
    page = (request.GET.get('page') or '1').strip()
    if page not in {'', '1'}:
        return ''
    q = (request.GET.get('q') or '').strip()
    if matches_stain_help_query(q):
        return q
    return ''


def seo(request):
    """Canonical без query-string; SITE_URL для абсолютных ссылок."""
    from catalog.seo import absolute_url, dumps_ld, organization_localbusiness_ld, site_origin

    try:
        settings_obj = SiteSettings.load()
    except Exception:  # noqa: BLE001
        settings_obj = SiteSettings(
            brand_name='УБИРАЕМСЯЛЕГКО',
            company_name='ООО СОЛНЕЧНЫЙ МЕЧ',
            phone='8-991-496-18-97',
            email='pro-brite_uss@mail.ru',
        )

    city_label = (getattr(settings_obj, 'city', None) or 'г. Уссурийск').strip()
    city_name = city_label.replace('г.', '').strip()

    return {
        'site_url': site_origin(request),
        'canonical_url': absolute_url(request, request.path),
        'default_og_image': absolute_url(request, '/static/img/og-image.jpg'),
        'org_json_ld': dumps_ld(organization_localbusiness_ld(settings_obj, request)),
        'meta_robots': '',
        'meta_keywords': meta_keywords_string(),
        'geo_region': 'RU-PRI',
        'geo_placename': f'{city_name}, {GEO_REGION}',
        'geo_region_label': GEO_REGION,
        'geo_region_short': GEO_REGION_SHORT,
        'stain_help_search_query': _stain_help_search_query(request),
        'stain_help_prefixes_json': json.dumps(
            list(STAIN_HELP_QUERY_PREFIXES),
            ensure_ascii=False,
        ),
    }
