from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


SITE_ACTIVITY_DAYS = 30


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь',
    )
    phone = models.CharField('Телефон', max_length=40, blank=True)
    last_site_visit_at = models.DateTimeField(
        'Последний вход на сайт',
        null=True,
        blank=True,
        db_index=True,
    )

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return f'Профиль {self.user.username}'

    @property
    def is_site_active(self) -> bool:
        """Активен, если заходил на витрину за последние 30 дней."""
        from django.utils import timezone
        from datetime import timedelta

        last = self.last_site_visit_at
        if last is None:
            last = self.user.last_login or self.user.date_joined
        if last is None:
            return False
        return last >= timezone.now() - timedelta(days=SITE_ACTIVITY_DAYS)


class DeliveryAddress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='delivery_addresses',
        verbose_name='Пользователь',
    )
    name = models.CharField('Название', max_length=100)
    address = models.CharField('Адрес', max_length=400)
    is_default = models.BooleanField('По умолчанию', default=False)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Адрес доставки'
        verbose_name_plural = 'Адреса доставки'
        ordering = ['-is_default', 'name', 'id']

    def __str__(self):
        return f'{self.name}: {self.address}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            DeliveryAddress.objects.filter(user_id=self.user_id).exclude(pk=self.pk).update(
                is_default=False
            )


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_user_profile(sender, instance, created, **kwargs):
    Profile.objects.get_or_create(user=instance)
