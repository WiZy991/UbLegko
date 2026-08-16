from decimal import Decimal
import logging
import re

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Count
from django.urls import reverse
from django.utils.text import slugify

from catalog.search_utils import build_product_search_text

logger = logging.getLogger(__name__)


def normalize_recommendation_codes(value: str | None) -> str:
    """Нормализует '1, 3,1, 5' → '1,3,5'."""
    text = str(value or '').strip()
    if not text:
        return ''
    numbers: list[int] = []
    seen: set[int] = set()
    for part in re.split(r'[,;\s]+', text):
        if not part:
            continue
        try:
            number = int(part)
        except ValueError:
            continue
        if number < 0 or number in seen:
            continue
        seen.add(number)
        numbers.append(number)
    return ','.join(str(n) for n in sorted(numbers))


def parse_recommendation_codes(value: str | None) -> set[int]:
    text = normalize_recommendation_codes(value)
    if not text:
        return set()
    return {int(part) for part in text.split(',') if part}

class Category(models.Model):
    name = models.CharField('Название', max_length=200)
    slug = models.SlugField(
        'Слаг',
        max_length=220,
        unique=True,
        blank=True,
        allow_unicode=True,
        help_text='Адрес страницы в URL. Можно оставить пустым — создастся из названия.',
    )
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    is_visible = models.BooleanField('Показывать', default=True)
    seo_title = models.CharField(
        'SEO title',
        max_length=255,
        blank=True,
        default='',
        help_text='Только для поисковиков (тег title). На витрине не показывается. Пусто — автошаблон.',
    )
    seo_description = models.CharField(
        'SEO description',
        max_length=320,
        blank=True,
        default='',
        help_text='Только для поисковиков (meta description). На витрине не показывается.',
    )
    seo_text = models.TextField(
        'SEO-текст (для meta)',
        blank=True,
        default='',
        help_text=(
            'Доп. текст только для meta description, если SEO description пустой. '
            'На странице сайта посетителям не показывается.'
        ),
    )

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.slug:
            self.slug = slugify(self.slug, allow_unicode=True)
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
        IN_STOCK = 'in_stock', 'В\u00a0наличии'
        IN_TRANSIT = 'in_transit', 'В\u00a0пути'
        OUT_OF_STOCK = 'out_of_stock', 'Нет\u00a0в\u00a0наличии'
        ON_ORDER = 'on_order', 'Под\u00a0заказ'

    name = models.CharField('Название', max_length=255)
    slug = models.SlugField(
        'Слаг',
        max_length=280,
        unique=True,
        blank=True,
        allow_unicode=True,
        help_text='Адрес страницы в URL. Можно оставить пустым — создастся из названия.',
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name='Категория',
    )
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
    image = models.ImageField(
        'Главное фото',
        upload_to='products/',
        blank=True,
        help_text='Показывается в каталоге и первым в галерее на странице товара',
    )
    image_card = models.ImageField(
        'Превью для каталога',
        upload_to='products/cards/',
        blank=True,
        editable=False,
        help_text='Автоматически создаётся из главного фото для быстрой загрузки каталога',
    )
    seo_title = models.CharField(
        'SEO title',
        max_length=255,
        blank=True,
        default='',
        help_text='Только для поисковиков (тег title). На витрине не показывается.',
    )
    seo_description = models.CharField(
        'SEO description',
        max_length=320,
        blank=True,
        default='',
        help_text='Только для поисковиков (meta description). На витрине не показывается.',
    )
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
    recommendation_codes = models.CharField(
        'Рекомендация',
        max_length=100,
        blank=True,
        default='',
        help_text=(
            'Номера групп через запятую, например: 1 или 1,3,5. '
            'Товары с общим номером показываются друг другу в рекомендациях на сайте.'
        ),
    )
    search_text = models.TextField('Поисковый индекс', blank=True, editable=False)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['category__sort_order', 'name']

    def __str__(self):
        return self.name

    def build_unique_slug(self, source: str | None = None) -> str:
        """Слаг из названия (или source), уникальный среди товаров."""
        base = slugify(source or self.name or '', allow_unicode=True) or 'product'
        slug = base
        n = 1
        while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f'{base}-{n}'
            n += 1
        return slug

    def save(self, *args, **kwargs):
        regenerate_slug = bool(getattr(self, '_regenerate_slug', False))
        if self.slug and not regenerate_slug:
            self.slug = slugify(self.slug, allow_unicode=True)
        if not self.slug or regenerate_slug:
            self.slug = self.build_unique_slug(self.name)
        # Старая цена → товар автоматически акционный (бэйдж на сайте).
        # Без старой цены — не акция.
        if self.old_price is not None and self.old_price > 0:
            self.is_promo = True
        else:
            self.is_promo = False
        self.recommendation_codes = normalize_recommendation_codes(self.recommendation_codes)
        self.search_text = build_product_search_text(
            name=self.name,
            description=self.description,
            sku=self.sku,
            country=self.country,
        )

        old_image_name = ''
        if self.pk:
            old_image_name = (
                Product.objects.filter(pk=self.pk)
                .values_list('image', flat=True)
                .first()
                or ''
            )
        new_image_name = self.image.name if self.image else ''
        image_changed = old_image_name != new_image_name
        uncommitted_image = bool(self.image) and not getattr(self.image, '_committed', True)
        update_fields = kwargs.get('update_fields')
        need_card = bool(self.image) and (
            uncommitted_image or image_changed or not self.image_card
        )

        super().save(*args, **kwargs)

        # Не гоняем превью при точечном save без image
        if update_fields is not None and 'image' not in update_fields:
            if not (self.image and not self.image_card):
                return
            need_card = not self.image_card

        try:
            from .image_utils import clear_card_image, ensure_card_image, persist_card_image

            if not self.image:
                if self.image_card:
                    clear_card_image(self)
                    persist_card_image(self)
                return

            if need_card and ensure_card_image(self, force=True):
                persist_card_image(self)
        except Exception:
            # Превью каталога не должно ломать сохранение/загрузку фото
            logger.exception(
                'Не удалось обновить image_card для product_id=%s',
                self.pk,
            )

    def get_recommendation_code_set(self) -> set[int]:
        return parse_recommendation_codes(self.recommendation_codes)

    def get_absolute_url(self):
        return reverse('catalog:product', kwargs={'slug': self.slug})

    @property
    def price_display(self):
        return f'{self.price:.0f} руб'

    @property
    def display_sku(self):
        """Код товара (артикул) для карточки — только реальное поле sku."""
        return (self.sku or '').strip()

    @property
    def card_description(self):
        """Первые 3 непустые строки полного описания для карточки каталога."""
        text = (self.description or '').strip()
        if not text:
            return ''
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            return ''
        from catalog.hyphenation import hyphenate_ru

        return hyphenate_ru('\n'.join(lines[:3]))

    def gallery_urls(self):
        """URL полных фото товара: главное + дополнительные, без дублей."""
        return [item['full'] for item in self.gallery_entries()]

    def gallery_entries(self):
        """
        Фото для страницы товара: preview (лёгкое) + full (оригинал).
        Если превью ещё нет — preview совпадает с full.
        """
        entries = []
        seen = set()

        if self.image:
            full = self.image.url
            preview = self.image_card.url if self.image_card else full
            entries.append({'preview': preview, 'full': full})
            seen.add(self.image.name)

        for item in self.images.all():
            if not item.image:
                continue
            if item.image.name in seen:
                continue
            full = item.image.url
            preview = item.image_card.url if item.image_card else full
            entries.append({'preview': preview, 'full': full})
            seen.add(item.image.name)

        return entries

    @property
    def display_image_url(self):
        """URL полного фото: главное или первое из галереи."""
        if self.image:
            return self.image.url
        for item in self.images.all():
            if item.image:
                return item.image.url
        return ''

    @property
    def card_image_url(self):
        """Лёгкое превью для каталога/корзины; иначе полный файл."""
        if self.image_card:
            return self.image_card.url
        return self.display_image_url

    @property
    def can_add_to_cart(self):
        """Можно ли увеличивать количество в корзине."""
        return self.status == self.Status.IN_STOCK

    @property
    def status_modifier(self):
        return {
            self.Status.IN_STOCK: 'in-stock',
            self.Status.IN_TRANSIT: 'in-transit',
            self.Status.OUT_OF_STOCK: 'out-of-stock',
            self.Status.ON_ORDER: 'on-order',
        }.get(self.status, '')


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='Товар',
    )
    image = models.ImageField('Фото', upload_to='products/gallery/')
    image_card = models.ImageField(
        'Превью для страницы товара',
        upload_to='products/gallery/cards/',
        blank=True,
        editable=False,
        help_text='Автоматически создаётся для быстрой первой отрисовки галереи',
    )
    sort_order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Фото'
        verbose_name_plural = 'Фото'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'Фото {self.pk} — {self.product}'

    def save(self, *args, **kwargs):
        old_image_name = ''
        if self.pk:
            old_image_name = (
                ProductImage.objects.filter(pk=self.pk)
                .values_list('image', flat=True)
                .first()
                or ''
            )
        new_image_name = self.image.name if self.image else ''
        image_changed = old_image_name != new_image_name
        uncommitted_image = bool(self.image) and not getattr(self.image, '_committed', True)
        update_fields = kwargs.get('update_fields')
        need_card = bool(self.image) and (
            uncommitted_image or image_changed or not self.image_card
        )

        super().save(*args, **kwargs)

        if update_fields is not None and 'image' not in update_fields:
            if not (self.image and not self.image_card):
                return
            need_card = not self.image_card

        try:
            from .image_utils import clear_card_image, ensure_card_image, persist_card_image

            if not self.image:
                if self.image_card:
                    clear_card_image(self)
                    persist_card_image(self)
                return

            if need_card and ensure_card_image(self, force=True):
                persist_card_image(self)
        except Exception:
            logger.exception(
                'Не удалось обновить image_card для ProductImage pk=%s',
                self.pk,
            )


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
