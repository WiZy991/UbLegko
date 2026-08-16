from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.db.models import Case, IntegerField, When
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import DetailView, ListView

from .export_xlsx import build_catalog_xlsx, catalog_xlsx_filename
from .filters import (
    apply_catalog_filters,
    has_active_filters,
    parse_catalog_filters,
)
from .forms import ProductReviewForm
from .models import Category, Product, ProductReview
from .pack_pricing import attach_price_per_liter
from .recommendations import get_recommendations_for_product
from .search_utils import filter_products_by_query, rank_prefix_first
from . import seo as seo_mod
from core.models import SiteSettings


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
        qs = Product.objects.filter(is_visible=True).select_related('category').prefetch_related('images')
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
        context['has_active_filters'] = has_active_filters(filters, context['sort'])
        context['scroll_spy_categories'] = False
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
        products = context.get('products') or context.get('object_list')
        if products is not None:
            attach_price_per_liter(products)
        return context


class HomeView(CatalogMixin, ListView):
    model = Product
    template_name = 'catalog/home.html'
    context_object_name = 'products'
    paginate_by = 48

    def get_paginate_by(self, queryset):
        # «По категориям» — все разделы целиком, в т.ч. с фильтрами «Акции» / «В наличии».
        sort = get_sort(self.request)
        if sort == 'category':
            return None
        return self.paginate_by

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sort = context['sort']
        products = list(context['products'])
        if sort == 'category':
            # Сохраняем порядок категорий из сайдбара (и при активных фильтрах)
            grouped = {}
            for category in context['categories']:
                grouped[category] = []
            for product in products:
                if product.category_id and product.category in grouped:
                    grouped[product.category].append(product)
                elif product.category_id:
                    grouped.setdefault(product.category, []).append(product)
            context['grouped_products'] = {
                category: items for category, items in grouped.items() if items
            }
            context['scroll_spy_categories'] = bool(context['grouped_products'])
            context['result_count'] = len(products)
        else:
            context['grouped_products'] = None
        ss = SiteSettings.load()
        context['page_title'] = seo_mod.home_meta_title(ss)
        context['page_description'] = seo_mod.home_meta_description(ss)
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
        ss = SiteSettings.load()
        context['page_title'] = seo_mod.category_meta_title(self.category, ss)
        context['page_description'] = seo_mod.category_meta_description(self.category)
        context['breadcrumb_json_ld'] = seo_mod.dumps_ld(
            seo_mod.breadcrumb_ld(
                [
                    ('Главная', '/'),
                    (self.category.name, self.category.get_absolute_url()),
                ],
                self.request,
            )
        )
        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = 'catalog/product_detail.html'
    context_object_name = 'product'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return (
            Product.objects.filter(is_visible=True)
            .select_related('category')
            .prefetch_related('images')
        )

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        try:
            from core.analytics import record_product_view

            record_product_view(request, self.object)
        except Exception:
            pass
        return response

    def get_user_review(self):
        if not self.request.user.is_authenticated:
            return None
        return ProductReview.objects.filter(
            product=self.object, user=self.request.user
        ).first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['gallery'] = self.object.gallery_entries()
        context['categories'] = Category.objects.filter(is_visible=True)
        context['recommendations'] = get_recommendations_for_product(self.object)
        context['similar_products'] = context['recommendations'].similar
        context['bought_together'] = context['recommendations'].bought_together
        context['reviews'] = (
            self.object.reviews.select_related('user').order_by('-created_at')
        )
        context['reviews_count'] = self.object.reviews.count()
        context['user_review'] = self.get_user_review()
        context['is_favorite'] = False
        if self.request.user.is_authenticated:
            from cart.models import Favorite

            context['is_favorite'] = Favorite.objects.filter(
                user=self.request.user, product=self.object
            ).exists()
            context['favorite_ids'] = set(
                Favorite.objects.filter(user=self.request.user).values_list('product_id', flat=True)
            )
            initial = {}
            if context['user_review']:
                initial = {
                    'rating': context['user_review'].rating,
                    'comment': context['user_review'].comment,
                }
            context['review_form'] = kwargs.get('review_form') or ProductReviewForm(initial=initial)
        else:
            context['favorite_ids'] = set()
            context['review_form'] = None
        attach_price_per_liter(
            [self.object, *context['similar_products'], *context['bought_together']]
        )
        ss = SiteSettings.load()
        product = self.object
        context['page_title'] = seo_mod.product_meta_title(product, ss)
        context['page_description'] = seo_mod.product_meta_description(product)
        og_image = ''
        if product.image:
            try:
                og_image = seo_mod.absolute_url(self.request, product.image.url)
            except Exception:
                og_image = ''
        if not og_image and product.image_card:
            try:
                og_image = seo_mod.absolute_url(self.request, product.image_card.url)
            except Exception:
                og_image = ''
        context['og_image_abs'] = og_image
        crumbs = [('Главная', '/')]
        if product.category_id:
            crumbs.append((product.category.name, product.category.get_absolute_url()))
        crumbs.append((product.name, product.get_absolute_url()))
        context['breadcrumb_json_ld'] = seo_mod.dumps_ld(
            seo_mod.breadcrumb_ld(crumbs, self.request)
        )
        context['product_json_ld'] = seo_mod.dumps_ld(
            seo_mod.product_ld(product, self.request, ss)
        )
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not request.user.is_authenticated:
            return redirect_to_login(self.object.get_absolute_url())

        if request.POST.get('action') == 'delete_review':
            deleted, _ = ProductReview.objects.filter(
                product=self.object, user=request.user
            ).delete()
            if deleted:
                from .models import update_product_rating

                update_product_rating(self.object.pk)
                messages.success(request, 'Ваш отзыв удалён')
            return redirect(self.object.get_absolute_url() + '#reviews')

        form = ProductReviewForm(request.POST)
        if form.is_valid():
            review, created = ProductReview.objects.update_or_create(
                product=self.object,
                user=request.user,
                defaults={
                    'rating': form.cleaned_data['rating'],
                    'comment': form.cleaned_data['comment'],
                },
            )
            # update_or_create may skip Model.save() path nuances — force rating recalc
            from .models import update_product_rating

            update_product_rating(self.object.pk)
            messages.success(
                request,
                'Отзыв обновлён' if not created else 'Спасибо! Ваш отзыв опубликован',
            )
            return redirect(self.object.get_absolute_url() + '#reviews')

        context = self.get_context_data(object=self.object, review_form=form)
        return self.render_to_response(context)


class SearchView(CatalogMixin, ListView):
    model = Product
    template_name = 'catalog/search.html'
    context_object_name = 'products'
    paginate_by = 48

    def get_queryset(self):
        qs = Product.objects.filter(is_visible=True).select_related('category').prefetch_related('images')
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
        return Product.objects.filter(id__in=ids).select_related('category').prefetch_related('images').order_by(order)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = getattr(self, 'query', '')
        return context


def search_suggest(request):
    """JSON-подсказки: название или описание (RU/EN)."""
    q = (request.GET.get('q') or '').strip()
    if len(q) < 1:
        return JsonResponse({'results': []})

    qs = Product.objects.filter(is_visible=True).select_related('category').prefetch_related('images')
    qs = filter_products_by_query(qs, q, prefix_only=True)
    ranked = rank_prefix_first(list(qs[:200]), q)[:10]
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


def download_catalog_xlsx(request):
    """Скачать весь видимый каталог в Excel с фото и полями с сайта."""
    payload = build_catalog_xlsx(site_origin=request.build_absolute_uri('/').rstrip('/'))
    filename = catalog_xlsx_filename()
    # ASCII filename= нужен Android Download Manager; filename*= — для кириллицы.
    ascii_name = 'price-ubiraemsya-legko.xlsx'
    encoded = quote(filename, safe='')
    response = HttpResponse(
        payload,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = (
        f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{encoded}'
    )
    response['Content-Length'] = str(len(payload))
    response['Cache-Control'] = 'no-store'
    return response
