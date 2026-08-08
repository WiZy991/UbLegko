from django.db.models import Case, IntegerField, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, ListView

from .filters import (
    PRICE_PRESETS,
    apply_catalog_filters,
    has_active_filters,
    parse_catalog_filters,
)
from .models import Category, Product
from .recommendations import get_recommendations_for_product
from .search_utils import filter_products_by_query, rank_prefix_first


SORT_OPTIONS = {
    'category': ('По категориям', ['category__sort_order', 'name']),
    'alpha': ('По алфавиту', ['name']),
    'popular': ('По популярности', ['-is_featured', '-rating', 'name']),
    'price_asc': ('Сначала дешевые', ['price', 'name']),
    'price_desc': ('Сначала дорогие', ['-price', 'name']),
}


def get_sort(request):
    sort = request.GET.get('sort', 'category')
    if sort not in SORT_OPTIONS:
        sort = 'category'
    return sort


class CatalogMixin:
    def get_filters(self):
        return parse_catalog_filters(self.request.GET)

    def get_queryset(self):
        qs = Product.objects.filter(is_visible=True).select_related('category')
        qs = apply_catalog_filters(qs, self.get_filters())
        sort = get_sort(self.request)
        return qs.order_by(*SORT_OPTIONS[sort][1])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = self.get_filters()
        context['categories'] = Category.objects.filter(is_visible=True)
        context['sort'] = get_sort(self.request)
        context['sort_options'] = SORT_OPTIONS
        context['filters'] = filters
        context['price_presets'] = PRICE_PRESETS
        context['has_active_filters'] = has_active_filters(filters)
        paginator = context.get('paginator')
        page_obj = context.get('page_obj')
        if paginator is not None:
            context['result_count'] = paginator.count
        elif page_obj is not None:
            context['result_count'] = page_obj.paginator.count
        else:
            context['result_count'] = len(context.get('products') or [])
        context['favorite_ids'] = set()
        if self.request.user.is_authenticated:
            from cart.models import Favorite

            context['favorite_ids'] = set(
                Favorite.objects.filter(user=self.request.user).values_list('product_id', flat=True)
            )
        return context


class HomeView(CatalogMixin, ListView):
    model = Product
    template_name = 'catalog/home.html'
    context_object_name = 'products'
    paginate_by = 48

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sort = context['sort']
        products = list(context['products'])
        if sort == 'category' and not context['has_active_filters']:
            grouped = {}
            for product in products:
                grouped.setdefault(product.category, []).append(product)
            context['grouped_products'] = grouped
        else:
            context['grouped_products'] = None
        return context


class CategoryView(CatalogMixin, ListView):
    model = Product
    template_name = 'catalog/category.html'
    context_object_name = 'products'
    paginate_by = 48

    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs['slug'], is_visible=True)
        return super().get_queryset().filter(category=self.category)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_category'] = self.category
        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = 'catalog/product_detail.html'
    context_object_name = 'product'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return Product.objects.filter(is_visible=True).select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(is_visible=True)
        context['recommendations'] = get_recommendations_for_product(self.object, limit=8)
        context['similar_products'] = context['recommendations'].similar
        context['bought_together'] = context['recommendations'].bought_together
        context['is_favorite'] = False
        if self.request.user.is_authenticated:
            from cart.models import Favorite

            context['is_favorite'] = Favorite.objects.filter(
                user=self.request.user, product=self.object
            ).exists()
            context['favorite_ids'] = set(
                Favorite.objects.filter(user=self.request.user).values_list('product_id', flat=True)
            )
        else:
            context['favorite_ids'] = set()
        return context


class SearchView(CatalogMixin, ListView):
    model = Product
    template_name = 'catalog/search.html'
    context_object_name = 'products'
    paginate_by = 48

    def get_queryset(self):
        qs = Product.objects.filter(is_visible=True).select_related('category')
        q = self.request.GET.get('q', '').strip()
        self.query = q
        filters = self.get_filters()
        sort = get_sort(self.request)

        if not q:
            qs = apply_catalog_filters(qs, filters)
            return qs.order_by(*SORT_OPTIONS[sort][1])

        qs = filter_products_by_query(qs, q, prefix_only=False)
        qs = apply_catalog_filters(qs, filters)

        ranked = rank_prefix_first(qs, q)
        ids = [p.id for p in ranked]
        if not ids:
            return Product.objects.none()

        order = Case(
            *[When(pk=pk, then=pos) for pos, pk in enumerate(ids)],
            output_field=IntegerField(),
        )
        return Product.objects.filter(id__in=ids).select_related('category').order_by(order)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = getattr(self, 'query', '')
        return context


def search_suggest(request):
    """JSON-подсказки: товары, у которых название начинается с запроса (RU/EN)."""
    q = (request.GET.get('q') or '').strip()
    if len(q) < 1:
        return JsonResponse({'results': []})

    qs = Product.objects.filter(is_visible=True).select_related('category')
    qs = filter_products_by_query(qs, q, prefix_only=True)
    ranked = rank_prefix_first(list(qs[:40]), q)[:10]
    results = [
        {
            'id': p.id,
            'name': p.name,
            'url': p.get_absolute_url(),
            'price': str(p.price),
            'category': p.category.name if p.category_id else '',
        }
        for p in ranked
    ]
    return JsonResponse({'results': results})
