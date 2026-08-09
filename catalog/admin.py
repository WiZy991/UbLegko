import csv
import io
import json
import re
from decimal import Decimal, InvalidOperation

from django.contrib import admin, messages
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import path
from django.utils.html import format_html, mark_safe
from openpyxl import load_workbook

from .categorize import resolve_category
from .models import Category, Product, ProductImage, ProductRecommendation, ProductReview

HEADER_ALIASES = {
    'name': {
        'name',
        'название',
        'наименование',
        'наименование товара',
        'товар',
    },
    'description': {
        'description',
        'описание',
        'описание товара',
    },
    'short_description': {
        'short_description',
        'краткое описание',
    },
    'price': {
        'price',
        'цена',
        'цена руб',
        'цена, руб',
    },
    'old_price': {
        'old_price',
        'старая цена',
        'цена старая',
    },
    'country': {
        'country',
        'страна',
        'страна производитель',
        'страна-производитель',
        'страна-произво-дитель',
        'производитель',
    },
    'sku': {
        'sku',
        'код',
        'код товара',
        'артикул',
    },
    'barcode': {
        'barcode',
        'штрихкод',
        'штрих-код',
        'ean',
    },
    'category': {
        'category',
        'категория',
        'раздел',
    },
    'status': {'status', 'статус'},
    'is_promo': {'is_promo', 'акция', 'promo'},
}


def normalize_header(value):
    text = str(value or '').strip().lower().replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text


def map_headers(raw_headers):
    mapping = {}
    for idx, header in enumerate(raw_headers):
        normalized = normalize_header(header)
        for field, aliases in HEADER_ALIASES.items():
            if normalized in aliases and field not in mapping:
                mapping[field] = idx
                break
    return mapping


def parse_price(value):
    if value is None or value == '':
        return None
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    text = str(value).strip().replace(' ', '').replace('руб', '').replace('₽', '')
    text = text.replace(',', '.')
    text = re.sub(r'[^0-9.\-]', '', text)
    if not text:
        return None
    return Decimal(text)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'sort_order', 'preview')
    readonly_fields = ('preview',)
    ordering = ('sort_order', 'id')
    verbose_name = 'Фото'
    verbose_name_plural = 'Дополнительные фотографии (можно добавить сколько угодно)'

    def preview(self, obj):
        if obj.pk and obj.image:
            return format_html(
                '<img src="{}" style="height:64px;width:64px;object-fit:cover;border-radius:6px;" />',
                obj.image.url,
            )
        return '—'

    preview.short_description = 'Превью'


class ProductRecommendationInline(admin.TabularInline):
    model = ProductRecommendation
    fk_name = 'product'
    extra = 1
    autocomplete_fields = ['recommended_product']
    verbose_name = 'Рекомендуем к этому товару'
    verbose_name_plural = 'Рекомендуем к этому товару'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('drag_handle', 'name', 'is_visible', 'products_count')
    list_display_links = ('name',)
    list_editable = ('is_visible',)
    list_filter = ('is_visible',)
    search_fields = ('name',)
    ordering = ('sort_order', 'name')
    prepopulated_fields = {'slug': ('name',)}
    change_list_template = 'admin/catalog/category/change_list.html'

    class Media:
        css = {'all': ('admin/css/category_sortable.css',)}

    @admin.display(description='')
    def drag_handle(self, obj):
        return mark_safe(
            '<span class="category-drag-handle" title="Перетащите для изменения порядка" aria-hidden="true">⠿</span>'
        )

    @admin.display(description='Товаров', ordering='products_count')
    def products_count(self, obj):
        return getattr(obj, 'products_count', obj.products.count())

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(products_count=Count('products'))

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'reorder/',
                self.admin_site.admin_view(self.reorder_view),
                name='catalog_category_reorder',
            ),
        ]
        return custom + urls

    def reorder_view(self, request):
        if request.method != 'POST':
            return JsonResponse({'ok': False, 'error': 'POST only'}, status=405)
        if not self.has_change_permission(request):
            return JsonResponse({'ok': False, 'error': 'Forbidden'}, status=403)
        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
            order = payload.get('order') or []
        except (TypeError, ValueError, json.JSONDecodeError):
            return JsonResponse({'ok': False, 'error': 'Bad JSON'}, status=400)

        ids = []
        for raw in order:
            try:
                ids.append(int(raw))
            except (TypeError, ValueError):
                continue

        existing = set(
            Category.objects.filter(pk__in=ids).values_list('pk', flat=True)
        )
        updates = []
        for index, pk in enumerate(ids):
            if pk not in existing:
                continue
            updates.append(Category(pk=pk, sort_order=index))
        if updates:
            Category.objects.bulk_update(updates, ['sort_order'])
        return JsonResponse({'ok': True, 'count': len(updates)})


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'category',
        'price',
        'old_price',
        'status',
        'is_promo',
        'is_visible',
        'thumb',
    )
    list_display_links = ('name',)
    list_filter = ('category', 'status', 'is_promo', 'is_visible', 'is_featured', 'country')
    list_editable = (
        'category',
        'price',
        'old_price',
        'status',
        'is_promo',
        'is_visible',
    )
    list_select_related = ('category',)
    list_per_page = 50
    search_fields = ('name', 'sku', 'barcode', 'short_description', 'description', 'country')
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ['category']
    inlines = [ProductImageInline, ProductRecommendationInline]
    change_list_template = 'admin/catalog/product/change_list.html'
    readonly_fields = ('rating', 'reviews_count')
    fieldsets = (
        (None, {
            'fields': (
                'name', 'slug', 'category', 'sku', 'barcode',
                'short_description', 'description',
                'unit', 'country', 'image',
            ),
        }),
        ('Цены и статус', {
            'fields': (
                'price',
                'old_price',
                'status',
                'rating',
                'reviews_count',
                'is_promo',
                'is_featured',
                'is_visible',
            ),
            'description': (
                'Для акционных товаров отметьте «Акция», укажите текущую цену в «Цена» '
                'и прежнюю — в «Старая цена» (зачёркнутая на сайте).'
            ),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category')

    def thumb(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:40px;width:40px;object-fit:cover;" />',
                obj.image.url,
            )
        return '—'

    thumb.short_description = 'Фото'

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'import/',
                self.admin_site.admin_view(self.import_view),
                name='catalog_product_import',
            ),
        ]
        return custom + urls

    def import_view(self, request):
        if request.method == 'POST' and request.FILES.get('file'):
            uploaded = request.FILES['file']
            filename = uploaded.name.lower()
            try:
                if filename.endswith('.csv'):
                    created, updated, errors = self._import_csv(uploaded)
                elif filename.endswith('.xlsx'):
                    created, updated, errors = self._import_xlsx(uploaded)
                elif filename.endswith('.xls'):
                    created, updated, errors = self._import_xls(uploaded)
                else:
                    messages.error(request, 'Поддерживаются файлы CSV, XLS и XLSX.')
                    return redirect('admin:catalog_product_import')
            except Exception as exc:  # noqa: BLE001
                messages.error(request, f'Ошибка импорта: {exc}')
                return redirect('admin:catalog_product_import')

            messages.success(
                request,
                f'Импорт завершён: создано {created}, обновлено {updated}. '
                'Товары автоматически распределены по категориям.',
            )
            for err in errors[:30]:
                messages.warning(request, err)
            return redirect('admin:catalog_product_changelist')

        context = {
            **self.admin_site.each_context(request),
            'title': 'Массовая загрузка товаров из Excel',
            'opts': self.model._meta,
        }
        return render(request, 'admin/catalog/product/import.html', context)

    def _parse_row(self, row, default_category=None):
        name = (row.get('name') or '').strip()
        if not name:
            raise ValueError('Пустое наименование товара')

        description = (row.get('description') or '').strip()
        short_description = (row.get('short_description') or '').strip()
        if not short_description and description:
            short_description = description[:300]

        explicit_category = (row.get('category') or '').strip()
        category = resolve_category(name, description, explicit_category)

        try:
            price = parse_price(row.get('price'))
        except InvalidOperation as exc:
            raise ValueError(f'Некорректная цена для «{name}»') from exc
        if price is None:
            raise ValueError(f'Нет цены для «{name}»')

        old_price = None
        try:
            old_price = parse_price(row.get('old_price'))
        except InvalidOperation:
            old_price = None

        status_raw = (row.get('status') or 'in_stock').strip().lower()
        status_map = {
            'in_stock': Product.Status.IN_STOCK,
            'в наличии': Product.Status.IN_STOCK,
            'in_transit': Product.Status.IN_TRANSIT,
            'в пути': Product.Status.IN_TRANSIT,
            'out_of_stock': Product.Status.OUT_OF_STOCK,
            'нет в наличии': Product.Status.OUT_OF_STOCK,
            'on_order': Product.Status.ON_ORDER,
            'под заказ': Product.Status.ON_ORDER,
        }
        status = status_map.get(status_raw, Product.Status.IN_STOCK)

        promo_raw = str(row.get('is_promo', '')).strip().lower()
        is_promo = promo_raw in {'1', 'true', 'yes', 'да', 'y'}
        if not is_promo and old_price and old_price > price:
            is_promo = True

        return {
            'name': name,
            'category': category,
            'price': price,
            'old_price': old_price,
            'description': description,
            'short_description': short_description,
            'unit': '',
            'country': (row.get('country') or '').strip(),
            'sku': '',
            'barcode': '',
            'status': status,
            'is_promo': is_promo,
            'is_visible': True,
        }

    def _upsert_product(self, data):
        product = None
        if data.get('sku'):
            product = Product.objects.filter(sku=data['sku']).first()
        if not product:
            product = Product.objects.filter(name=data['name']).first()
        if product:
            for key, value in data.items():
                setattr(product, key, value)
            product.save()
            return False
        Product.objects.create(**data)
        return True

    def _import_mapped_rows(self, headers, data_rows, default_category=None, start_row=2):
        mapping = map_headers(headers)
        if 'name' not in mapping or 'price' not in mapping:
            raise ValueError(
                'В файле должны быть столбцы «Наименование товара» и «Цена». '
                f'Найдены: {headers}'
            )
        created = updated = 0
        errors = []
        for offset, values in enumerate(data_rows):
            row_number = start_row + offset
            if not values or all(v is None or str(v).strip() == '' for v in values):
                continue
            row = {}
            for field, idx in mapping.items():
                if idx < len(values):
                    value = values[idx]
                    row[field] = '' if value is None else value
            try:
                data = self._parse_row(row)
                if self._upsert_product(data):
                    created += 1
                else:
                    updated += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(f'Строка {row_number}: {exc}')
        return created, updated, errors

    def _import_csv(self, uploaded, default_category=None):
        content = uploaded.read().decode('utf-8-sig')
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        if not rows:
            return 0, 0, ['Пустой файл']
        return self._import_mapped_rows(rows[0], rows[1:])

    def _import_xlsx(self, uploaded, default_category=None):
        wb = load_workbook(uploaded, read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return 0, 0, ['Пустой файл']
        return self._import_mapped_rows(rows[0], rows[1:])

    def _import_xls(self, uploaded, default_category=None):
        import xlrd

        book = xlrd.open_workbook(file_contents=uploaded.read())
        sheet = book.sheet_by_index(0)
        if sheet.nrows < 2:
            return 0, 0, ['Пустой файл']
        headers = [sheet.cell_value(0, c) for c in range(sheet.ncols)]
        data_rows = [
            [sheet.cell_value(r, c) for c in range(sheet.ncols)]
            for r in range(1, sheet.nrows)
        ]
        return self._import_mapped_rows(headers, data_rows)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('thumb', 'product', 'sort_order', 'image')
    list_editable = ('sort_order',)
    list_filter = ('product__category',)
    search_fields = ('product__name', 'product__sku', 'product__barcode', 'image')
    autocomplete_fields = ['product']
    list_select_related = ('product',)
    list_per_page = 50
    change_list_template = 'admin/catalog/productimage/change_list.html'

    @admin.display(description='Превью')
    def thumb(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:48px;width:48px;object-fit:cover;border-radius:6px;" />',
                obj.image.url,
            )
        return '—'

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'bulk-upload/',
                self.admin_site.admin_view(self.bulk_upload_view),
                name='catalog_productimage_bulk_upload',
            ),
        ]
        return custom + urls

    def bulk_upload_view(self, request):
        from .photo_import import assign_photos, iter_upload_files

        if request.method == 'POST':
            zip_file = request.FILES.get('zip_file')
            files = request.FILES.getlist('images') + request.FILES.getlist('folder_images')
            replace_main = request.POST.get('replace_main') == '1'

            if not zip_file and not files:
                messages.error(request, 'Выберите ZIP-архив или файлы/папку с фото.')
                return redirect('admin:catalog_productimage_bulk_upload')

            try:
                items = list(iter_upload_files(files, zip_file=zip_file))
            except Exception as exc:  # noqa: BLE001
                messages.error(request, f'Не удалось прочитать файлы: {exc}')
                return redirect('admin:catalog_productimage_bulk_upload')

            if not items:
                messages.error(
                    request,
                    'Не найдено изображений. Поддерживаются JPG, PNG, WEBP, GIF, BMP, TIFF.',
                )
                return redirect('admin:catalog_productimage_bulk_upload')

            result = assign_photos(items, replace_main=replace_main)
            messages.success(
                request,
                f'Готово: главных фото — {result.assigned_main}, '
                f'в галерею — {result.assigned_gallery}.',
            )
            for name in result.unmatched[:40]:
                messages.warning(request, f'Не найден товар для файла: {name}')
            if len(result.unmatched) > 40:
                messages.warning(
                    request,
                    f'…и ещё {len(result.unmatched) - 40} файлов без совпадения.',
                )
            for err in result.errors[:20]:
                messages.error(request, err)
            for skip in result.skipped[:10]:
                messages.info(request, skip)
            return redirect('admin:catalog_productimage_changelist')

        context = {
            **self.admin_site.each_context(request),
            'title': 'Массовая загрузка фото',
            'opts': self.model._meta,
        }
        return render(request, 'admin/catalog/productimage/bulk_upload.html', context)


@admin.register(ProductRecommendation)
class ProductRecommendationAdmin(admin.ModelAdmin):
    list_display = ('product', 'recommended_product', 'sort_order')
    autocomplete_fields = ['product', 'recommended_product']


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('product__name', 'user__username', 'comment')
    autocomplete_fields = ['product', 'user']
    readonly_fields = ('created_at', 'updated_at')
