from django.core.management.base import BaseCommand

from core.models import City


class Command(BaseCommand):
    help = 'Оставляет активным только г. Уссурийск'

    def handle(self, *args, **options):
        City.objects.update(is_default=False, is_active=False)

        ussuriysk, created = City.objects.update_or_create(
            name='Уссурийск',
            defaults={
                'region': 'Приморский край',
                'note': '',
                'is_default': True,
                'is_active': True,
                'sort_order': 0,
            },
        )
        # На всякий случай отключаем «Другие города» и прочие записи
        City.objects.exclude(pk=ussuriysk.pk).update(is_active=False, is_default=False)

        action = 'создан' if created else 'обновлён'
        self.stdout.write(
            self.style.SUCCESS(f'Активен только {ussuriysk.display_name} ({action})')
        )
