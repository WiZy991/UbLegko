from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = 'Убираемся Легко — админпанель'
admin.site.site_title = 'Убираемся Легко'
admin.site.index_title = 'Управление сайтом'

from cart.views import favorites

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('catalog.urls')),
    path('cart/', include('cart.urls')),
    path('favorites/', favorites, name='favorites'),
    path('accounts/', include('accounts.urls')),
    path('', include('core.urls')),
]

handler404 = 'core.views_errors.page_not_found'
handler500 = 'core.views_errors.server_error'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
