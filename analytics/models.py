from core.models import ProductPageView, SearchQueryLog


class SiteStatistics(ProductPageView):
    class Meta:
        proxy = True
        app_label = 'analytics'
        verbose_name = 'По сайту'
        verbose_name_plural = 'По сайту'


class SearchStatistics(SearchQueryLog):
    class Meta:
        proxy = True
        app_label = 'analytics'
        verbose_name = 'По поиску'
        verbose_name_plural = 'По поиску'
