from django.http import HttpResponse
from django.views.decorators.http import require_GET

from catalog.seo import site_origin


@require_GET
def robots_txt(request):
    """
    Правила для роботов. Админка и служебные разделы не индексируем.
    Sitemap — только публичный каталог (товары/категории), без /admin/.
    """
    origin = site_origin(request)
    lines = [
        'User-agent: *',
        'Allow: /',
        # Админка полностью вне SEO / индексации
        'Disallow: /admin/',
        'Disallow: /admin',
        'Disallow: /cart/',
        'Disallow: /accounts/',
        'Disallow: /favorites/',
        'Disallow: /search/',
        'Disallow: /search/suggest/',
        'Disallow: /set-city/',
        'Disallow: /stain-help/',
        f'Sitemap: {origin}/sitemap.xml',
        '',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain; charset=utf-8')
