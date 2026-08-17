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


YANDEX_VERIFY_HTML = (
    '<html>\n'
    '    <head>\n'
    '        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">\n'
    '    </head>\n'
    '    <body>Verification: a48eb77a88713753</body>\n'
    '</html>\n'
)


@require_GET
def yandex_verify(request):
    """HTML-файл для подтверждения прав в Яндекс.Вебмастере."""
    return HttpResponse(YANDEX_VERIFY_HTML, content_type='text/html; charset=UTF-8')
