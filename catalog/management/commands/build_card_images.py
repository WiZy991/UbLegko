from django.core.management.base import BaseCommand
from django.db.models import Q

from catalog.image_utils import ensure_card_image
from catalog.models import Product


class Command(BaseCommand):
    help = (
        'Разовая догонка: создаёт image_card для старых товаров без превью. '
        'Новые загрузки главного фото обрабатываются сами в Product.save().'
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
            help='Ограничить число товаров (0 = все)',
        )

    def handle(self, *args, **options):
        force = options['force']
        limit = options['limit']

        qs = Product.objects.exclude(image='').exclude(image__isnull=True).order_by('id')
        if not force:
            qs = qs.filter(Q(image_card='') | Q(image_card__isnull=True))

        pks = list(qs.values_list('pk', flat=True))
        if limit > 0:
            pks = pks[:limit]

        self.stdout.write(f'Товаров к обработке: {len(pks)}')
        done = 0
        errors = 0
        for pk in pks:
            try:
                product = Product.objects.get(pk=pk)
                if ensure_card_image(product, force=True):
                    # Пишем только поле превью, без повторной генерации в save()
                    Product.objects.filter(pk=pk).update(image_card=product.image_card.name)
                    done += 1
                    if done % 25 == 0:
                        self.stdout.write(f'… {done}')
            except Exception as exc:
                errors += 1
                self.stderr.write(f'Ошибка product_id={pk}: {exc}')

        self.stdout.write(self.style.SUCCESS(f'Готово: обновлено {done}, ошибок {errors}'))
