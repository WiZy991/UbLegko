"""Превью фото для каталога и быстрой отрисовки страницы товара."""

from __future__ import annotations

import logging
import uuid
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from django.utils.text import slugify
from PIL import Image, ImageFile, ImageOps

logger = logging.getLogger(__name__)

CARD_MAX_SIDE = 600
CARD_QUALITY = 80

ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = 500_000_000


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


def _open_stored_file(field_file):
    """Читает уже сохранённый файл со склада, а не буфер загрузки."""
    if not field_file or not field_file.name:
        raise ValueError('Нет файла изображения')
    try:
        field_file.close()
    except Exception:
        pass
    field_file._file = None
    return field_file.storage.open(field_file.name, 'rb')


def clear_card_image(instance) -> None:
    if not getattr(instance, 'image_card', None):
        return
    try:
        instance.image_card.delete(save=False)
    except Exception:
        logger.exception(
            'Не удалось удалить image_card для %s pk=%s',
            instance.__class__.__name__,
            getattr(instance, 'pk', None),
        )
    instance.image_card = None


def persist_card_image(instance) -> None:
    """Пишет путь image_card в БД без повторного Model.save()."""
    type(instance).objects.filter(pk=instance.pk).update(
        image_card=instance.image_card.name if instance.image_card else '',
    )


def ensure_card_image(instance, *, force: bool = False) -> bool:
    """
    Создаёт/обновляет instance.image_card из instance.image.
    Работает для Product и ProductImage.
    Возвращает True, если поле изменилось и его нужно сохранить.
    """
    if not instance.image:
        if instance.image_card:
            clear_card_image(instance)
            return True
        return False

    if instance.image_card and not force:
        return False

    try:
        with _open_stored_file(instance.image) as src:
            data, ext = build_card_image_bytes(src)
    except Exception:
        logger.exception(
            'Не удалось прочитать оригинал для card preview %s pk=%s name=%s',
            instance.__class__.__name__,
            getattr(instance, 'pk', None),
            getattr(instance.image, 'name', ''),
        )
        return False

    # Уникальное имя: иначе после смены главного URL превью тот же → браузер/CDN
    # отдают старую картинку, хотя в админке уже новое полное фото.
    stem = slugify(Path(instance.image.name).stem, allow_unicode=False) or 'photo'
    filename = f'{stem}-{instance.pk or "new"}-{uuid.uuid4().hex[:10]}.{ext}'

    if instance.image_card:
        try:
            instance.image_card.delete(save=False)
        except Exception:
            pass
        instance.image_card = None

    try:
        instance.image_card.save(filename, ContentFile(data), save=False)
    except Exception:
        logger.exception(
            'Не удалось сохранить image_card для %s pk=%s',
            instance.__class__.__name__,
            getattr(instance, 'pk', None),
        )
        return False
    return True
