from django.core.management.base import BaseCommand
from django.db.models import Q

from catalog.image_utils import ensure_card_image, persist_card_image
from catalog.models import Product, ProductImage


class Command(BaseCommand):
    help = (
        'Разовая догонка: создаёт image_card для главных фото и фото галереи. '
        'Новые загрузки обрабатываются сами в Model.save().'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Пересоздать превью даже если уже есть',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Ограничить число записей каждого типа (0 = все)',
        )
        parser.add_argument(
            '--gallery-only',
            action='store_true',
            help='Только фото галереи (ProductImage)',
        )
        parser.add_argument(
            '--main-only',
            action='store_true',
            help='Только главные фото товаров (Product)',
        )

    def handle(self, *args, **options):
        force = options['force']
        limit = options['limit']
        gallery_only = options['gallery_only']
        main_only = options['main_only']

        if not gallery_only:
            self._build_products(force=force, limit=limit)
        if not main_only:
            self._build_gallery(force=force, limit=limit)

    def _build_products(self, *, force: bool, limit: int) -> None:
        qs = Product.objects.exclude(image='').exclude(image__isnull=True).order_by('id')
        if not force:
            qs = qs.filter(Q(image_card='') | Q(image_card__isnull=True))

        pks = list(qs.values_list('pk', flat=True))
        if limit > 0:
            pks = pks[:limit]

        self.stdout.write(f'Главных фото к обработке: {len(pks)}')
        done = 0
        errors = 0
        for pk in pks:
            try:
                product = Product.objects.get(pk=pk)
                if ensure_card_image(product, force=True):
                    persist_card_image(product)
                    done += 1
                    if done % 25 == 0:
                        self.stdout.write(f'… products {done}')
            except Exception as exc:
                errors += 1
                self.stderr.write(f'Ошибка product_id={pk}: {exc}')

        self.stdout.write(self.style.SUCCESS(f'Главные: обновлено {done}, ошибок {errors}'))

    def _build_gallery(self, *, force: bool, limit: int) -> None:
        qs = ProductImage.objects.exclude(image='').exclude(image__isnull=True).order_by('id')
        if not force:
            qs = qs.filter(Q(image_card='') | Q(image_card__isnull=True))

        pks = list(qs.values_list('pk', flat=True))
        if limit > 0:
            pks = pks[:limit]

        self.stdout.write(f'Фото галереи к обработке: {len(pks)}')
        done = 0
        errors = 0
        for pk in pks:
            try:
                item = ProductImage.objects.get(pk=pk)
                if ensure_card_image(item, force=True):
                    persist_card_image(item)
                    done += 1
                    if done % 25 == 0:
                        self.stdout.write(f'… gallery {done}')
            except Exception as exc:
                errors += 1
                self.stderr.write(f'Ошибка ProductImage id={pk}: {exc}')

        self.stdout.write(self.style.SUCCESS(f'Галерея: обновлено {done}, ошибок {errors}'))
