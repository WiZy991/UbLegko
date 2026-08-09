from django.core.management.base import BaseCommand

from core.models import City


class Command(BaseCommand):
    help = 'Оставляет активным только Уссурийск'

    def handle(self, *args, **options):
        City.objects.update(is_default=False, is_active=False)
        obj, created = City.objects.update_or_create(
            name='Уссурийск',
            defaults={
                'region': 'Приморский край',
                'is_default': True,
                'is_active': True,
                'sort_order': 0,
            },
        )
        action = 'создан' if created else 'обновлён'
        self.stdout.write(self.style.SUCCESS(f'Город Уссурийск {action}; остальные отключены'))
