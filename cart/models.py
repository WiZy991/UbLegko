from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from catalog.models import Product


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Пользователь',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name='Товар',
    )
    created_at = models.DateTimeField('Добавлен', auto_now_add=True)

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        unique_together = [('user', 'product')]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} — {self.product}'


class OrderYearCounter(models.Model):
    """Счётчик номеров новых заявок по календарным годам (Asia/Vladivostok)."""

    year = models.PositiveSmallIntegerField('Год', primary_key=True)
    last_number = models.PositiveIntegerField('Последний №', default=0)

    class Meta:
        verbose_name = 'Счётчик заявок'
        verbose_name_plural = 'Счётчики заявок'

    def __str__(self):
        return f'{self.year}: {self.last_number}'


def _vladivostok_year(dt=None):
    if dt is None:
        dt = timezone.now()
    return timezone.localtime(dt).year


def assign_order_number(order):
    year = _vladivostok_year()
    with transaction.atomic():
        counter, _ = OrderYearCounter.objects.select_for_update().get_or_create(
            year=year,
            defaults={'last_number': 0},
        )
        counter.last_number += 1
        counter.save(update_fields=['last_number'])
        order.number = counter.last_number
        order.number_year = year


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'Новая'
        PROCESSED = 'processed', 'Обработана'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Пользователь',
    )
    full_name = models.CharField('Имя', max_length=200)
    phone = models.CharField('Телефон', max_length=40)
    email = models.EmailField('Email', blank=True)
    delivery_method = models.CharField(
        'Способ получения',
        max_length=20,
        choices=[
            ('courier', 'Курьером'),
            ('pickup', 'Самовывоз'),
        ],
        default='courier',
    )
    address = models.CharField('Адрес доставки', max_length=400, blank=True)
    address_name = models.CharField('Название адреса', max_length=100, blank=True)
    city = models.CharField('Город', max_length=120, blank=True)
    comment = models.TextField('Комментарий', blank=True)
    site_feedback = models.TextField('Замечания по сайту', blank=True)
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )
    email_sent = models.BooleanField('Письмо отправлено', default=False)
    number = models.PositiveIntegerField('№', editable=False)
    number_year = models.PositiveSmallIntegerField('Год №', editable=False)
    created_at = models.DateTimeField('Создана', auto_now_add=True)

    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['number_year', 'number'],
                name='cart_order_unique_number_per_year',
            ),
        ]

    def save(self, *args, **kwargs):
        if self._state.adding and not self.number:
            assign_order_number(self)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Заявка №{self.number} ({self.number_year}) — {self.full_name}'

    @property
    def total(self):
        return sum(item.line_total for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Заявка',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Товар',
    )
    product_name = models.CharField('Название товара', max_length=255)
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField('Количество', default=1)

    class Meta:
        verbose_name = 'Позиция заявки'
        verbose_name_plural = 'Позиции заявки'

    def __str__(self):
        return f'{self.product_name} × {self.quantity}'

    @property
    def line_total(self):
        return self.price * self.quantity


class StainHelpRequest(models.Model):
    """Обращение из формы «Что-то не отмывается, просто скажите»."""

    full_name = models.CharField('Имя', max_length=200)
    phone = models.CharField('Телефон', max_length=40)
    contact_method = models.CharField('Способ связи', max_length=300)
    problem = models.TextField('Что не отмывается')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stain_help_requests',
        verbose_name='Пользователь',
    )
    email_sent = models.BooleanField('Письмо отправлено', default=False)
    is_processed = models.BooleanField('Обработано', default=False)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        # Таблица создана как core_stainhelprequest — оставляем имя, чтобы не ломать данные.
        db_table = 'core_stainhelprequest'
        verbose_name = 'Запрос'
        verbose_name_plural = 'Запросы'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.full_name} — {self.phone} ({self.created_at:%d.%m.%Y %H:%M})'
