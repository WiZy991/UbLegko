from django.core.management.base import BaseCommand

from catalog.models import Product
from catalog.search_utils import build_product_search_text


class Command(BaseCommand):
    help = 'Пересобрать search_text у всех товаров (включая SEO-фразы и гео Приморского края).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Ограничить число товаров (0 = все)',
        )

    def handle(self, *args, **options):
        qs = Product.objects.select_related('category').order_by('pk')
        limit = options['limit']
        if limit:
            qs = qs[:limit]

        products = list(qs)
        updated = 0
        for product in products:
            category_name = product.category.name if product.category_id else ''
            new_text = build_product_search_text(
                name=product.name,
                description=product.description,
                sku=product.sku,
                country=product.country,
                category_name=category_name,
            )
            if product.search_text != new_text:
                Product.objects.filter(pk=product.pk).update(search_text=new_text)
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(f'Готово: обновлено {updated} из {len(products)} товаров.')
        )
