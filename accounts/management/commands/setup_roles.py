from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from accounts.roles import (
    ALL_MANAGED_GROUP_NAMES,
    SEGMENT_BASE,
    ensure_default_groups,
    set_user_membership,
)


class Command(BaseCommand):
    help = 'Создаёт стандартные группы и синхронизирует членство пользователей'

    def handle(self, *args, **options):
        groups = ensure_default_groups()
        for key, group in groups.items():
            self.stdout.write(self.style.SUCCESS(f'OK: {group.name} ({key})'))

        synced = 0
        for user in User.objects.all().iterator():
            if user.is_superuser:
                set_user_membership(user, 'admin')
                synced += 1
            elif user.is_staff:
                set_user_membership(user, 'staff')
                synced += 1
            else:
                names = set(user.groups.values_list('name', flat=True))
                if not names.intersection(ALL_MANAGED_GROUP_NAMES):
                    # Обычные пользователи без группы → Клиенты
                    set_user_membership(user, SEGMENT_BASE)
                    synced += 1

        self.stdout.write(self.style.SUCCESS(f'Синхронизировано пользователей: {synced}'))
