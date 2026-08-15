from django.urls import path, register_converter

from . import views


class UnicodeSlugConverter:
    regex = r'[-a-zA-Z0-9_\u0400-\u04FF]+'

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(UnicodeSlugConverter, 'uslug')

app_name = 'catalog'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('price-ubiraemsya-legko.xlsx', views.download_catalog_xlsx, name='download_xlsx'),
    # Старый адрес — чтобы закладки/ссылки не ломались
    path('catalog.xlsx', views.download_catalog_xlsx),
    path('category/<uslug:slug>/', views.CategoryView.as_view(), name='category'),
    path('product/<uslug:slug>/', views.ProductDetailView.as_view(), name='product'),
    path('search/', views.SearchView.as_view(), name='search'),
    path('search/suggest/', views.search_suggest, name='search_suggest'),
]
