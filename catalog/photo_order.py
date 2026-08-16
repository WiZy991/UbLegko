"""Порядок дополнительных фото товара (галерея) и смена главного."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction

from .models import Product, ProductImage

logger = logging.getLogger(__name__)


def apply_product_photo_order(product: Product, tokens: list[str]) -> bool:
    """
    Сохраняет порядок галереи по списку токенов gallery:<id>.
    Главное фото не меняется. Возвращает True, если порядок изменился.
    """
    gallery = list(
        ProductImage.objects.filter(product=product).order_by('sort_order', 'id')
    )
    if not gallery:
        return False

    by_id = {image.pk: image for image in gallery}
    ordered: list[ProductImage] = []
    seen: set[int] = set()

    for raw in tokens:
        token = str(raw or '').strip()
        if not token.startswith('gallery:'):
            continue
        try:
            image_id = int(token.split(':', 1)[1])
        except (TypeError, ValueError):
            continue
        image = by_id.get(image_id)
        if image and image.pk not in seen:
            ordered.append(image)
            seen.add(image.pk)

    for image in gallery:
        if image.pk not in seen:
            ordered.append(image)

    updates = []
    for index, image in enumerate(ordered):
        if image.sort_order != index:
            image.sort_order = index
            updates.append(image)

    if not updates:
        return False

    ProductImage.objects.bulk_update(updates, ['sort_order'])
    return True


def _read_storage_bytes(name: str) -> bytes:
    with default_storage.open(name, 'rb') as fh:
        return fh.read()


def _safe_delete_storage(name: str | None) -> None:
    if not name:
        return
    try:
        if default_storage.exists(name):
            default_storage.delete(name)
    except Exception:
        logger.exception('Не удалось удалить файл %s', name)


def promote_gallery_image_to_main(product: Product, gallery_image: ProductImage) -> None:
    """
    Меняет местами главное фото и выбранное из галереи.

    Важно: сначала читаем оба файла в память, потом пишем новые пути.
    Нельзя удалять главное до записи — из‑за этого ломался обмен.
    """
    from .image_utils import clear_card_image, ensure_card_image, persist_card_image

    if not gallery_image.image or not gallery_image.image.name:
        raise ValueError('Фото галереи не найдено')

    gallery_path = gallery_image.image.name
    gallery_bytes = _read_storage_bytes(gallery_path)
    if not gallery_bytes:
        raise ValueError('Пустой файл галереи')

    main_path = product.image.name if product.image else ''
    main_bytes = _read_storage_bytes(main_path) if main_path else None
    main_card_path = product.image_card.name if product.image_card else ''
    gallery_card_path = (
        gallery_image.image_card.name if gallery_image.image_card else ''
    )
    keep_sort = gallery_image.sort_order
    gallery_pk = gallery_image.pk

    suffix = Path(gallery_path).suffix.lower() or '.jpg'
    if suffix not in {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}:
        suffix = '.jpg'

    with transaction.atomic():
        # 1) Новое главное из байтов галереи (старое главное на диске ещё живо)
        new_main_name = f'main-{product.pk}-{uuid.uuid4().hex[:10]}{suffix}'
        product.image.save(new_main_name, ContentFile(gallery_bytes), save=False)
        if product.image_card:
            clear_card_image(product)
        product.save()
        if ensure_card_image(product, force=True):
            persist_card_image(product)

        new_main_path = product.image.name if product.image else ''

        # 2) Убираем строку галереи, которая стала главной
        gallery_image.image.delete(save=False)
        if gallery_image.image_card:
            gallery_image.image_card.delete(save=False)
        ProductImage.objects.filter(pk=gallery_pk).delete()

        # 3) Бывшее главное — в галерею на то же место
        if main_bytes:
            demoted_suffix = Path(main_path).suffix.lower() or '.jpg'
            if demoted_suffix not in {
                '.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp',
            }:
                demoted_suffix = '.jpg'
            demoted = ProductImage(product=product, sort_order=keep_sort)
            demoted_name = (
                f'gallery-{product.pk}-{uuid.uuid4().hex[:10]}{demoted_suffix}'
            )
            demoted.image.save(demoted_name, ContentFile(main_bytes), save=True)

        # 4) Удаляем осиротевшие старые файлы главного (уже скопированы)
        if main_path and main_path != new_main_path:
            _safe_delete_storage(main_path)
        if main_card_path:
            _safe_delete_storage(main_card_path)
        # gallery_path / gallery_card уже удалены через FieldFile.delete
        _safe_delete_storage(gallery_path)
        _safe_delete_storage(gallery_card_path)
