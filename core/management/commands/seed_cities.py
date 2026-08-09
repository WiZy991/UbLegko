from django.core.management.base import BaseCommand

from core.models import City


class Command(BaseCommand):
    help = 'Настраивает города: Уссурийск и «Другие города (доставка)»'

    def handle(self, *args, **options):
        City.objects.update(is_default=False, is_active=False)

        ussuriysk, _ = City.objects.update_or_create(
            name='Уссурийск',
            defaults={
                'region': 'Приморский край',
                'note': '',
                'is_default': True,
                'is_active': True,
                'sort_order': 0,
            },
        )
        other, _ = City.objects.update_or_create(
            name='Другие города',
            defaults={
                'region': '',
                'note': 'Доставка в другие города',
                'is_default': False,
                'is_active': True,
                'sort_order': 10,
            },
        )
        # Старые лишние города остаются неактивными
        self.stdout.write(
            self.style.SUCCESS(
                f'Активны: {ussuriysk.display_name}, {other.display_name}'
            )
        )
