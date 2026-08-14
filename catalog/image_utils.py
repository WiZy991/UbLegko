"""Превью главного фото для карточек каталога."""

from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

CARD_MAX_SIDE = 600
CARD_QUALITY = 80


def _open_rgb(source) -> Image.Image:
    img = Image.open(source)
    img = ImageOps.exif_transpose(img)
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        rgba = img.convert('RGBA')
        background = Image.new('RGB', rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        return background
    return img.convert('RGB')


def build_card_image_bytes(source) -> tuple[bytes, str]:
    """
    Уменьшает изображение до CARD_MAX_SIDE.
    Возвращает (bytes, extension) — предпочтительно webp, иначе jpg.
    """
    img = _open_rgb(source)
    img.thumbnail((CARD_MAX_SIDE, CARD_MAX_SIDE), Image.Resampling.LANCZOS)

    buf = BytesIO()
    try:
        img.save(buf, format='WEBP', quality=CARD_QUALITY, method=4)
        return buf.getvalue(), 'webp'
    except Exception:
        buf = BytesIO()
        img.save(buf, format='JPEG', quality=CARD_QUALITY, optimize=True)
        return buf.getvalue(), 'jpg'


def clear_card_image(product) -> None:
    if not getattr(product, 'image_card', None):
        return
    try:
        product.image_card.delete(save=False)
    except Exception:
        logger.exception('Не удалось удалить image_card для product_id=%s', product.pk)
    product.image_card = None


def ensure_card_image(product, *, force: bool = False) -> bool:
    """
    Создаёт/обновляет product.image_card из product.image.
    Возвращает True, если поле изменилось и его нужно сохранить.
    """
    if not product.image:
        if product.image_card:
            clear_card_image(product)
            return True
        return False

    if product.image_card and not force:
        return False

    try:
        product.image.open('rb')
        try:
            data, ext = build_card_image_bytes(product.image)
        finally:
            product.image.close()
    except Exception:
        logger.exception(
            'Не удалось прочитать оригинал для card preview product_id=%s',
            product.pk,
        )
        return False

    stem = Path(product.image.name).stem or f'product-{product.pk or "new"}'
    filename = f'{stem}.{ext}'

    if product.image_card:
        try:
            product.image_card.delete(save=False)
        except Exception:
            pass

    product.image_card.save(filename, ContentFile(data), save=False)
    return True
