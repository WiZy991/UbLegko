import csv
import io
import re
from decimal import Decimal, InvalidOperation

from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path
from django.utils.html import format_html
from openpyxl import load_workbook

from .categorize import resolve_category
from .models import Category, Product, ProductRecommendation, ProductReview

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
    'unit': {
        'unit',
        'ед',
        'ед.',
        'ед. изм.',
        'ед.изм.',
        'ед измерения',
        'ед. измерения',
        'единица измерения',
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


class ProductRecommendationInline(admin.TabularInline):
    model = ProductRecommendation
    fk_name = 'product'
    extra = 1
    autocomplete_fields = ['recommended_product']
    verbose_name = 'Рекомендуем к этому товару'
    verbose_name_plural = 'Рекомендуем к этому товару'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'sort_order', 'is_visible')
    list_editable = ('sort_order', 'is_visible')
    list_filter = ('is_visible',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'category',
        'price',
        'unit',
        'country',
        'status',
        'is_promo',
        'is_visible',
        'thumb',
    )
    list_filter = ('category', 'status', 'is_promo', 'is_visible', 'is_featured', 'country', 'unit')
    list_editable = ('status', 'is_promo', 'is_visible')
    search_fields = ('name', 'sku', 'barcode', 'short_description', 'description', 'country')
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ['category']
    inlines = [ProductRecommendationInline]
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
            'fields': ('price', 'old_price', 'status', 'rating', 'reviews_count', 'is_promo', 'is_featured', 'is_visible'),
        }),
    )

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
            'unit': (row.get('unit') or 'шт').strip() or 'шт',
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
