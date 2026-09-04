from django.core.management.base import BaseCommand

from accounts.roles import ensure_default_groups


class Command(BaseCommand):
    help = 'Создаёт стандартные группы: Администраторы, Персонал, VIP, Постоянные, Клиенты'

    def handle(self, *args, **options):
        groups = ensure_default_groups()
        for key, group in groups.items():
            self.stdout.write(self.style.SUCCESS(f'OK: {group.name} ({key})'))
