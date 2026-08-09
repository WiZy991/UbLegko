from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Count
from django.urls import reverse
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField('Название', max_length=200)
    slug = models.SlugField('Слаг', max_length=220, unique=True, blank=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    is_visible = models.BooleanField('Показывать', default=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name, allow_unicode=True) or 'category'
            slug = base
            n = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('catalog:category', kwargs={'slug': self.slug})


class Product(models.Model):
    class Status(models.TextChoices):
        IN_STOCK = 'in_stock', 'В наличии'
        IN_TRANSIT = 'in_transit', 'В пути'
        OUT_OF_STOCK = 'out_of_stock', 'Нет в наличии'
        ON_ORDER = 'on_order', 'Под заказ'

    name = models.CharField('Название', max_length=255)
    slug = models.SlugField('Слаг', max_length=280, unique=True, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name='Категория',
    )
    short_description = models.CharField('Краткое описание', max_length=300, blank=True)
    description = models.TextField('Описание', blank=True)
    unit = models.CharField('Ед. измерения', max_length=50, blank=True, default='')
    country = models.CharField('Страна производитель', max_length=100, blank=True)
    sku = models.CharField('Код товара', max_length=100, blank=True, db_index=True)
    barcode = models.CharField('Штрихкод', max_length=64, blank=True)
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    old_price = models.DecimalField(
        'Старая цена',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    image = models.ImageField('Изображение', upload_to='products/', blank=True)
    rating = models.DecimalField('Рейтинг', max_digits=3, decimal_places=1, default=Decimal('0'))
    reviews_count = models.PositiveIntegerField('Число оценок', default=0)
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=Status.choices,
        default=Status.IN_STOCK,
    )
    is_promo = models.BooleanField('Акция', default=False)
    is_visible = models.BooleanField('Показывать в каталоге', default=True)
    is_featured = models.BooleanField('Популярный', default=False)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['category__sort_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name, allow_unicode=True) or 'product'
            slug = base
            n = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('catalog:product', kwargs={'slug': self.slug})

    @property
    def price_display(self):
        return f'{self.price:.0f} руб'


class ProductRecommendation(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='recommendations',
        verbose_name='Товар',
    )
    recommended_product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='recommended_for',
        verbose_name='Рекомендуемый товар',
    )
    sort_order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Рекомендация'
        verbose_name_plural = 'Рекомендации'
        ordering = ['sort_order', 'id']
        unique_together = [('product', 'recommended_product')]

    def __str__(self):
        return f'{self.product} → {self.recommended_product}'


class ProductReview(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Товар',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='product_reviews',
        verbose_name='Пользователь',
    )
    rating = models.PositiveSmallIntegerField(
        'Оценка',
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField('Комментарий', max_length=2000)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлён', auto_now=True)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']
        unique_together = [('product', 'user')]

    def __str__(self):
        return f'{self.product} — {self.rating}★ ({self.user})'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        update_product_rating(self.product_id)

    def delete(self, *args, **kwargs):
        product_id = self.product_id
        super().delete(*args, **kwargs)
        update_product_rating(product_id)


def update_product_rating(product_id):
    agg = ProductReview.objects.filter(product_id=product_id).aggregate(
        avg=Avg('rating'),
        cnt=Count('id'),
    )
    count = int(agg['cnt'] or 0)
    if count == 0 or agg['avg'] is None:
        Product.objects.filter(pk=product_id).update(rating=Decimal('0'), reviews_count=0)
        return
    Product.objects.filter(pk=product_id).update(
        rating=Decimal(str(round(float(agg['avg']), 1))),
        reviews_count=count,
    )
