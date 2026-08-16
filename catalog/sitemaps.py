from django.contrib.sitemaps import Sitemap

from .models import Category, Product


class StaticViewSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 1.0
    protocol = None

    def items(self):
        return ['home', 'contacts']

    def location(self, item):
        if item == 'home':
            return '/'
        return '/contacts/'


class CategorySitemap(Sitemap):
    """Все видимые категории каталога."""

    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Category.objects.filter(is_visible=True).order_by('sort_order', 'name')

    def location(self, obj):
        return obj.get_absolute_url()


class ProductSitemap(Sitemap):
    """
    Все товары каталога, доступные на сайте (is_visible=True).
    Без лимита: в sitemap попадает полный видимый ассортимент.
    Скрытые товары не включаем — их страницы отдают 404.
    """

    changefreq = 'daily'
    priority = 0.7
    # Django по умолчанию режет sitemap на куски по 50000 URL — этого достаточно

    def items(self):
        return (
            Product.objects.filter(is_visible=True)
            .only('id', 'slug', 'created_at')
            .order_by('id')
        )

    def location(self, obj):
        return obj.get_absolute_url()

    def lastmod(self, obj):
        return getattr(obj, 'created_at', None)
