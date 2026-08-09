from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь',
    )
    phone = models.CharField('Телефон', max_length=40, blank=True)

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return f'Профиль {self.user.username}'


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
