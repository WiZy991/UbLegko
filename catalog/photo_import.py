"""Массовая привязка фото к товарам по имени файла."""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from django.core.files.base import ContentFile
from django.utils.text import slugify

from .models import Product, ProductImage

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tif', '.tiff'}

# Суффикс доп. фото: _2 или (2). Дефис не используем — в артикулах часто есть «-».
SUFFIX_RE = re.compile(
    r'^(?P<base>.+?)(?:_(?P<num>\d+)|\s*\((?P<num2>\d+)\))?$',
    re.UNICODE,
)


def normalize_key(value: str) -> str:
    text = (value or '').strip().lower().replace('ё', 'е')
    text = re.sub(r'[\s_\-]+', ' ', text)
    text = re.sub(r'[^\w\s.+]', '', text, flags=re.UNICODE)
    return text.strip()


def parse_filename(filename: str) -> tuple[str, int]:
    """Возвращает (ключ для поиска товара, порядковый номер фото)."""
    stem = Path(filename).stem.strip()
    match = SUFFIX_RE.match(stem)
    if not match:
        return stem, 0
    base = (match.group('base') or stem).strip()
    num_raw = match.group('num') or match.group('num2') or '0'
    try:
        num = int(num_raw)
    except ValueError:
        num = 0
    # Если весь stem — число, это не суффикс
    if normalize_key(base) == '' and stem.isdigit():
        return stem, 0
    return base, max(num, 0)


@dataclass
class PhotoImportResult:
    assigned_main: int = 0
    assigned_gallery: int = 0
    skipped: list[str] = field(default_factory=list)
    unmatched: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class ProductPhotoMatcher:
    def __init__(self):
        self.by_sku: dict[str, Product] = {}
        self.by_barcode: dict[str, Product] = {}
        self.by_slug: dict[str, Product] = {}
        self.by_name: dict[str, Product] = {}
        self.by_name_slug: dict[str, Product] = {}

        for product in Product.objects.all().only(
            'id', 'name', 'slug', 'sku', 'barcode', 'image'
        ):
            if product.sku:
                self.by_sku[normalize_key(product.sku)] = product
            if product.barcode:
                self.by_barcode[normalize_key(product.barcode)] = product
            if product.slug:
                self.by_slug[normalize_key(product.slug)] = product
                self.by_slug[product.slug.lower()] = product
            name_key = normalize_key(product.name)
            if name_key:
                self.by_name[name_key] = product
            name_slug = slugify(product.name, allow_unicode=True)
            if name_slug:
                self.by_name_slug[normalize_key(name_slug)] = product
                self.by_name_slug[name_slug.lower()] = product

    def find(self, base_name: str) -> Product | None:
        key = normalize_key(base_name)
        if not key:
            return None
        for mapping in (
            self.by_sku,
            self.by_barcode,
            self.by_slug,
            self.by_name,
            self.by_name_slug,
        ):
            product = mapping.get(key)
            if product:
                return product

        # Без пробелов / с дефисами как в slug файла
        compact = key.replace(' ', '')
        slug_like = slugify(base_name, allow_unicode=True).lower()
        for mapping in (self.by_sku, self.by_barcode, self.by_slug, self.by_name_slug):
            for candidate_key, product in mapping.items():
                if candidate_key.replace(' ', '') == compact:
                    return product
                if candidate_key == slug_like:
                    return product
        return None


def iter_upload_files(uploaded_files, zip_file=None):
    """Yields (original_name, bytes_content) from multi-upload and/or zip."""
    if zip_file is not None:
        raw = zip_file.read()
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = info.filename
                # Skip macOS junk
                if name.startswith('__MACOSX/') or Path(name).name.startswith('._'):
                    continue
                ext = Path(name).suffix.lower()
                if ext not in IMAGE_EXTENSIONS:
                    continue
                yield Path(name).name, zf.read(info)

    for uploaded in uploaded_files or []:
        name = getattr(uploaded, 'name', '') or ''
        # Folder upload may include relative path: folder/sku.jpg
        basename = Path(name).name
        if basename.startswith('._'):
            continue
        ext = Path(basename).suffix.lower()
        if ext not in IMAGE_EXTENSIONS:
            continue
        yield basename, uploaded.read()


def assign_photos(file_items, *, replace_main: bool = False) -> PhotoImportResult:
    """
    Привязывает фото к товарам.
    Первый подходящий файл (или с номером 1/0) без главного фото → главное.
    Остальные → галерея. Если replace_main=True, главное фото перезаписывается.
    """
    result = PhotoImportResult()
    matcher = ProductPhotoMatcher()

    # Группируем по найденному товару
    grouped: dict[int, list[tuple[int, str, bytes]]] = {}
    for filename, content in file_items:
        if not content:
            result.skipped.append(f'{filename}: пустой файл')
            continue
        base, order_num = parse_filename(filename)
        product = matcher.find(base)
        if product is None:
            result.unmatched.append(filename)
            continue
        grouped.setdefault(product.pk, []).append((order_num, filename, content))

    products = {
        p.pk: p
        for p in Product.objects.filter(pk__in=grouped.keys())
    }

    for product_id, items in grouped.items():
        product = products[product_id]
        items.sort(key=lambda x: (x[0], x[1].lower()))
        next_gallery_order = (
            ProductImage.objects.filter(product_id=product_id)
            .order_by('-sort_order')
            .values_list('sort_order', flat=True)
            .first()
            or 0
        )
        main_filled = False

        for order_num, filename, content in items:
            ext = Path(filename).suffix.lower() or '.jpg'
            safe_stem = slugify(Path(filename).stem, allow_unicode=True) or 'photo'
            save_name = f'{safe_stem}{ext}'

            try:
                use_as_main = False
                if not main_filled:
                    if replace_main or not product.image:
                        use_as_main = True

                if use_as_main:
                    product.image.save(save_name, ContentFile(content), save=True)
                    result.assigned_main += 1
                    main_filled = True
                    continue

                next_gallery_order += 1
                img = ProductImage(product=product, sort_order=next_gallery_order)
                img.image.save(save_name, ContentFile(content), save=True)
                result.assigned_gallery += 1
                main_filled = True
            except Exception as exc:  # noqa: BLE001
                result.errors.append(f'{filename}: {exc}')

    return result
