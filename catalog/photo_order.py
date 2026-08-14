"""Порядок дополнительных фото товара (галерея). Главное не трогаем."""

from __future__ import annotations

from .models import Product, ProductImage


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
