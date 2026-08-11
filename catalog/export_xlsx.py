"""Выгрузка публичного каталога в Excel с фотографиями."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
from openpyxl.drawing.xdr import XDRPositiveSize2D
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils.units import pixels_to_EMU
from PIL import Image as PILImage

from .models import Product

COL_WIDTHS = {
    'A': 16,
    'B': 14,
    'C': 36,
    'D': 44,
    'E': 10,
    'F': 12,
    'G': 10,
    'H': 14,
}
ROW_HEIGHT = 100
PHOTO_THUMB = (78, 78)
BADGE_THUMB = (40, 40)
# Картинка занимает не больше этой доли ячейки — иначе Excel рисует поверх границ
MAX_CELL_FILL = 0.58


def catalog_xlsx_filename() -> str:
    """Имя файла для скачивания (без двоеточия — Windows его запрещает)."""
    today = timezone.localdate().strftime('%d.%m.%y')
    return f'Прайс магазина Убираемся легко по состоянию на {today}.xlsx'


def _col_width_px(excel_width: float) -> int:
    return max(1, int(excel_width * 7 + 5))


def _row_height_px(points: float) -> int:
    return max(1, int(points * 96 / 72))


def _badge_akciya_path() -> Path | None:
    candidates = [
        Path(settings.BASE_DIR) / 'static' / 'img' / 'badge-akciya.png',
        Path(settings.STATIC_ROOT) / 'img' / 'badge-akciya.png' if settings.STATIC_ROOT else None,
    ]
    for path in candidates:
        if path and path.is_file():
            return path
    return None


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


def _thumb_png_bytes(path: Path, thumb_size: tuple[int, int]) -> tuple[BytesIO, int, int] | None:
    """Уменьшенная картинка (без огромного холста). Возвращает буфер и фактический размер."""
    try:
        with PILImage.open(path) as img:
            img = img.convert('RGBA')
            img.thumbnail(thumb_size, PILImage.Resampling.LANCZOS)
            # Белый квадрат ровно под картинку — без лишних полей
            out = PILImage.new('RGB', img.size, (255, 255, 255))
            out.paste(img, (0, 0), img)
            buf = BytesIO()
            out.save(buf, format='PNG', optimize=True)
            buf.seek(0)
            return buf, out.width, out.height
    except Exception:
        return None


def _add_image_centered_in_cell(
    ws,
    buf: BytesIO,
    *,
    col_idx: int,
    row_idx: int,
    col_width_excel: float,
    row_height_pt: float,
    img_w: int,
    img_h: int,
) -> None:
    """Ставит картинку по центру ячейки с запасом от границ (не перекрывает линии)."""
    cell_w = _col_width_px(col_width_excel)
    cell_h = _row_height_px(row_height_pt)

    max_w = max(12, int(cell_w * MAX_CELL_FILL))
    max_h = max(12, int(cell_h * MAX_CELL_FILL))
    scale = min(max_w / img_w, max_h / img_h, 1.0)
    disp_w = max(1, int(img_w * scale))
    disp_h = max(1, int(img_h * scale))

    offset_x = max(0, (cell_w - disp_w) // 2)
    offset_y = max(0, (cell_h - disp_h) // 2)

    img = XLImage(buf)
    img.width = disp_w
    img.height = disp_h
    marker = AnchorMarker(
        col=col_idx - 1,
        colOff=pixels_to_EMU(offset_x),
        row=row_idx - 1,
        rowOff=pixels_to_EMU(offset_y),
    )
    size = XDRPositiveSize2D(pixels_to_EMU(disp_w), pixels_to_EMU(disp_h))
    img.anchor = OneCellAnchor(_from=marker, ext=size)
    ws.add_image(img)


def build_catalog_xlsx(*, site_origin: str = '') -> bytes:
    products = list(
        Product.objects.filter(is_visible=True)
        .select_related('category')
        .prefetch_related('images')
        .order_by('category__sort_order', 'category__name', 'name')
    )

    wb = Workbook()
    ws = wb.active
    ws.title = 'Прайс'

    headers = [
        'Фото',
        'Артикул',
        'Название',
        'Описание',
        'Цена',
        'Акция',
        'Рейтинг',
        'Страна',
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

    for letter, width in COL_WIDTHS.items():
        ws.column_dimensions[letter].width = width

    ws.row_dimensions[1].height = 22
    ws.freeze_panes = 'A2'

    image_buffers: list[BytesIO] = []
    badge_path = _badge_akciya_path()

    for row_idx, product in enumerate(products, start=2):
        is_promo = bool(product.is_promo or (product.old_price and product.old_price > 0))
        path = _product_image_path(product)
        if path:
            result = _thumb_png_bytes(path, PHOTO_THUMB)
            if result:
                buf, iw, ih = result
                image_buffers.append(buf)
                _add_image_centered_in_cell(
                    ws,
                    buf,
                    col_idx=1,
                    row_idx=row_idx,
                    col_width_excel=COL_WIDTHS['A'],
                    row_height_pt=ROW_HEIGHT,
                    img_w=iw,
                    img_h=ih,
                )

        if is_promo and badge_path:
            result = _thumb_png_bytes(badge_path, BADGE_THUMB)
            if result:
                buf, iw, ih = result
                image_buffers.append(buf)
                _add_image_centered_in_cell(
                    ws,
                    buf,
                    col_idx=6,
                    row_idx=row_idx,
                    col_width_excel=COL_WIDTHS['F'],
                    row_height_pt=ROW_HEIGHT,
                    img_w=iw,
                    img_h=ih,
                )

        values = [
            '',
            product.sku or '',
            product.name,
            product.description or '',
            float(product.price) if product.price is not None else '',
            '',
            float(product.rating) if product.rating is not None else '',
            product.country or '',
        ]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row_idx, col, value)
            cell.border = thin
            cell.alignment = center if col in (1, 2, 5, 6, 7, 8) else wrap

        ws.row_dimensions[row_idx].height = ROW_HEIGHT

    ws.oddHeader.center.text = (
        f'Прайс магазина Убираемся легко по состоянию на '
        f'{timezone.localdate().strftime("%d.%m.%y")} · товаров: {len(products)}'
    )

    out = BytesIO()
    wb.save(out)
    _ = image_buffers
    return out.getvalue()
