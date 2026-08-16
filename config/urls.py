from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from cart.views import favorites
from catalog.sitemaps import CategorySitemap, ProductSitemap, StaticViewSitemap
from core.views_seo import robots_txt

admin.site.site_header = 'Убираемся Легко — админпанель'
admin.site.site_title = 'Убираемся Легко'
admin.site.index_title = 'Управление сайтом'

sitemaps = {
    'static': StaticViewSitemap,
    'categories': CategorySitemap,
    'products': ProductSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('robots.txt', robots_txt, name='robots_txt'),
    path(
        'sitemap.xml',
        sitemap,
        {'sitemaps': sitemaps},
        name='django.contrib.sitemaps.views.sitemap',
    ),
    path('', include('catalog.urls')),
    path('cart/', include('cart.urls')),
    path('favorites/', favorites, name='favorites'),
    path('accounts/', include('accounts.urls')),
    path('', include('core.urls')),
]

handler404 = 'core.views_errors.page_not_found'
handler500 = 'core.views_errors.server_error'

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
