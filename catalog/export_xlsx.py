"""Выгрузка публичного каталога в Excel с фотографиями."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from PIL import Image as PILImage

from .models import Product

THUMB_SIZE = (120, 120)
ROW_HEIGHT = 92
IMAGE_DISPLAY = 88


def _product_image_path(product: Product) -> Path | None:
    if product.image:
        path = Path(product.image.path)
        if path.is_file():
            return path
    for item in product.images.all():
        if not item.image:
            continue
        path = Path(item.image.path)
        if path.is_file():
            return path
    return None


def _thumb_bytes(path: Path) -> BytesIO | None:
    try:
        with PILImage.open(path) as img:
            img = img.convert('RGB')
            img.thumbnail(THUMB_SIZE, PILImage.Resampling.LANCZOS)
            buf = BytesIO()
            img.save(buf, format='JPEG', quality=80, optimize=True)
            buf.seek(0)
            return buf
    except Exception:
        return None


def build_catalog_xlsx(*, site_origin: str = '') -> bytes:
    products = list(
        Product.objects.filter(is_visible=True)
        .select_related('category')
        .prefetch_related('images')
        .order_by('category__sort_order', 'category__name', 'name')
    )

    wb = Workbook()
    ws = wb.active
    ws.title = 'Каталог'

    headers = [
        'Фото',
        'Категория',
        'Название',
        'Код товара',
        'Штрихкод',
        'Описание',
        'Ед. изм.',
        'Страна',
        'Цена, руб',
        'Старая цена, руб',
        'Статус',
        'Акция',
        'Рейтинг',
        'Оценок',
        'Ссылка',
    ]
    header_font = Font(bold=True, color='FFFFFF')
    header_fill = PatternFill('solid', fgColor='0F6F86')
    thin = Border(
        left=Side(style='thin', color='D0D0D0'),
        right=Side(style='thin', color='D0D0D0'),
        top=Side(style='thin', color='D0D0D0'),
        bottom=Side(style='thin', color='D0D0D0'),
    )
    wrap = Alignment(wrap_text=True, vertical='center')
    center = Alignment(horizontal='center', vertical='center', wrap_text=True)

    for col, title in enumerate(headers, start=1):
        cell = ws.cell(1, col, title)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = thin

    ws.row_dimensions[1].height = 22
    ws.freeze_panes = 'A2'

    # Буферы живут до wb.save — openpyxl читает их при записи
    image_buffers: list[BytesIO] = []
    origin = (site_origin or '').rstrip('/')

    for row_idx, product in enumerate(products, start=2):
        path = _product_image_path(product)
        if path:
            buf = _thumb_bytes(path)
            if buf:
                image_buffers.append(buf)
                xl_img = XLImage(buf)
                xl_img.width = IMAGE_DISPLAY
                xl_img.height = IMAGE_DISPLAY
                ws.add_image(xl_img, f'A{row_idx}')

        link = product.get_absolute_url()
        if origin:
            link = f'{origin}{link}'

        values = [
            '',
            product.category.name if product.category_id else '',
            product.name,
            product.sku or '',
            product.barcode or '',
            product.description or '',
            product.unit or '',
            product.country or '',
            float(product.price) if product.price is not None else '',
            float(product.old_price) if product.old_price is not None else '',
            product.get_status_display(),
            'Да' if product.is_promo else 'Нет',
            float(product.rating) if product.rating is not None else '',
            product.reviews_count or 0,
            link,
        ]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row_idx, col, value)
            cell.border = thin
            cell.alignment = center if col in (1, 9, 10, 11, 12, 13, 14) else wrap

        ws.row_dimensions[row_idx].height = ROW_HEIGHT

    widths = {
        'A': 14,
        'B': 22,
        'C': 36,
        'D': 14,
        'E': 16,
        'F': 42,
        'G': 10,
        'H': 14,
        'I': 12,
        'J': 14,
        'K': 14,
        'L': 10,
        'M': 10,
        'N': 10,
        'O': 42,
    }
    for letter, width in widths.items():
        ws.column_dimensions[letter].width = width

    ws.oddHeader.center.text = (
        f'Каталог · {timezone.localtime().strftime("%d.%m.%Y %H:%M")} · товаров: {len(products)}'
    )

    out = BytesIO()
    wb.save(out)
    # image_buffers referenced until here
    _ = image_buffers
    return out.getvalue()
