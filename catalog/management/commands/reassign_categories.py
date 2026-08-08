from django.core.management.base import BaseCommand

from catalog.categorize import reassign_imported_products


class Command(BaseCommand):
    help = 'Перераспределяет товары из «Импортированные товары» по категориям и удаляет этот раздел'

    def handle(self, *args, **options):
        moved, left = reassign_imported_products()
        self.stdout.write(self.style.SUCCESS(f'Перенесено товаров: {moved}'))
        if left:
            self.stdout.write(self.style.WARNING('Раздел «Импортированные товары» ещё существует'))
        else:
            self.stdout.write(self.style.SUCCESS('Раздел «Импортированные товары» удалён'))
