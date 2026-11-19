"""Полная выгрузка товаров в Excel без картинок — для бэкапа и обратной загрузки."""

from __future__ import annotations

from io import BytesIO

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

from .models import Product

# Заголовки совпадают с алиасами импорта в catalog/admin.py
COLUMNS = (
    ('id', 'id', 10),
    ('name', 'Название', 42),
    ('slug', 'Слаг', 28),
    ('category', 'Категория', 28),
    ('sku', 'Код товара', 16),
    ('barcode', 'Штрихкод', 18),
    ('unit', 'Ед. измерения', 16),
    ('country', 'Страна производитель', 22),
    ('price', 'Цена', 12),
    ('old_price', 'Старая цена', 14),
    ('status', 'Статус', 16),
    ('description', 'Описание товара', 48),
    ('price_tag_description', 'Описание для ценника', 48),
    ('is_promo', 'Акция', 10),
    ('is_new', 'Новинка', 12),
    ('is_hit', 'Хит продаж', 14),
    ('is_visible', 'Показывать в каталоге', 22),
    ('is_featured', 'Популярный', 14),
    ('recommendation_codes', 'Рекомендация', 16),
    ('seo_title', 'SEO title', 28),
    ('seo_description', 'SEO description', 36),
    ('rating', 'Рейтинг', 12),
    ('reviews_count', 'Число оценок', 14),
)


def products_database_filename() -> str:
    today = timezone.localtime().strftime('%d.%m.%Y')
    return f'База товаров Убираемся легко на {today}.xlsx'


def _cell_value(product: Product, field: str):
    if field == 'category':
        return product.category.name if product.category_id else ''
    if field in {'is_promo', 'is_new', 'is_hit', 'is_visible', 'is_featured'}:
        return 1 if getattr(product, field) else 0
    if field in {'price', 'old_price', 'rating'}:
        value = getattr(product, field)
        return float(value) if value is not None else ''
    value = getattr(product, field)
    return '' if value is None else value


def build_products_database_xlsx() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = 'Товары'
    header_font = Font(bold=True)
    wrap = Alignment(wrap_text=True, vertical='top')

    for col, (_field, title, width) in enumerate(COLUMNS, start=1):
        cell = ws.cell(1, col, title)
        cell.font = header_font
        ws.column_dimensions[get_column_letter(col)].width = width

    products = (
        Product.objects.select_related('category')
        .order_by('name', 'id')
        .iterator(chunk_size=500)
    )
    row_idx = 2
    for product in products:
        for col, (field, _title, _width) in enumerate(COLUMNS, start=1):
            cell = ws.cell(row_idx, col, _cell_value(product, field))
            if field in {'description', 'price_tag_description', 'seo_description'}:
                cell.alignment = wrap
        row_idx += 1

    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f'A1:{get_column_letter(len(COLUMNS))}{max(row_idx - 1, 1)}'

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
