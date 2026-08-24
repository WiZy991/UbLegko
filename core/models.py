from django.db import models


class City(models.Model):
    name = models.CharField('Город', max_length=120)
    region = models.CharField('Регион', max_length=120, blank=True, default='Приморский край')
    note = models.CharField(
        'Подпись',
        max_length=200,
        blank=True,
        help_text='Например: «Доставка в другие города»',
    )
    is_default = models.BooleanField('По умолчанию', default=False)
    is_active = models.BooleanField('Активен', default=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Город'
        verbose_name_plural = 'Города'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    @property
    def display_name(self):
        if self.name.startswith('г.') or self.name.startswith('г '):
            return self.name
        if self.note or 'друг' in self.name.lower():
            return self.name
        return f'г. {self.name}'

    def save(self, *args, **kwargs):
        if self.is_default:
            City.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class SiteSettings(models.Model):
    company_name = models.CharField('Название компании', max_length=200, default='ООО СОЛНЕЧНЫЙ МЕЧ')
    brand_name = models.CharField('Бренд', max_length=100, default='УБИРАЕМСЯЛЕГКО')
    slogan = models.CharField(
        'Слоган',
        max_length=255,
        default='Что-то не отмывается, просто скажите',
    )
    tagline = models.CharField(
        'Подзаголовок',
        max_length=255,
        default='профессиональные моющие средства для дома и организаций',
    )
    phone = models.CharField('Телефон', max_length=40, default='8-991-496-18-97')
    email = models.EmailField('Email', default='pro-brite_uss@mail.ru')
    order_email = models.EmailField('Email для заявок', default='pro-brite_uss@mail.ru')
    city = models.CharField('Город (текст в футере)', max_length=100, default='г. Уссурийск')
    address = models.CharField(
        'Адрес',
        max_length=300,
        default='ул. Горького 91, ст4 (вход с ул. Амурская)',
    )
    full_address = models.CharField(
        'Полный адрес',
        max_length=400,
        default='Приморский край, г. Уссурийск, ул. Горького 91, ст4, магазин «Убираемсялегко»',
    )
    working_hours = models.CharField(
        'Часы работы',
        max_length=100,
        default='с 9.00 до 20.00 (без выходных)',
    )
    inn = models.CharField('ИНН', max_length=20, default='2511130194')
    ogrn = models.CharField('ОГРН', max_length=20, default='1242500027120')
    max_channel_url = models.URLField(
        'Ссылка на канал MAX',
        blank=True,
        default='https://max.ru/join/5n4w4WgqNIhX-fh4J5fjF5-NeJ_q728An7crUD3gF08',
    )
    stain_help_auto_modal = models.BooleanField(
        'Активировать автоматически модальное окно',
        default=False,
        help_text=(
            'Если включено, посетитель один раз за визит увидит форму '
            '«Что-то не отмывается» сразу при входе на сайт. '
            'Дальше окно открывается только по нажатию на слоган.'
        ),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Настройки сайта'
        verbose_name_plural = 'Настройки сайта'

    def __str__(self):
        return 'Настройки сайта'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SiteVisit(models.Model):
    """Заход на сайт (любая страница витрины). Каждая запись — один заход."""

    path = models.CharField('Страница', max_length=300, blank=True)
    visited_at = models.DateTimeField('Когда', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Заход на сайт'
        verbose_name_plural = 'Заходы на сайт'
        indexes = [
            models.Index(fields=['visited_at']),
        ]

    def __str__(self):
        return f'{self.path or "/"} @ {self.visited_at:%Y-%m-%d %H:%M}'


class ProductPageView(models.Model):
    """Просмотр карточки товара (для статистики в админке)."""

    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='page_views',
        verbose_name='Товар',
    )
    visitor_key = models.CharField('Посетитель', max_length=64, db_index=True)
    viewed_at = models.DateTimeField('Когда', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Статистика'
        verbose_name_plural = 'Статистика'
        indexes = [
            models.Index(fields=['viewed_at', 'product']),
            models.Index(fields=['product', 'visitor_key', 'viewed_at']),
        ]

    def __str__(self):
        return f'{self.product_id} @ {self.viewed_at:%Y-%m-%d %H:%M}'


class SearchQueryLog(models.Model):
    """Запрос из поисковой строки на сайте. Хранится 7 дней."""

    query = models.CharField('Запрос', max_length=200)
    query_norm = models.CharField('Запрос (нормализованный)', max_length=200, db_index=True)
    created_at = models.DateTimeField('Когда', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Статистика по поиску'
        verbose_name_plural = 'Статистика по поиску'
        indexes = [
            models.Index(fields=['query_norm', 'created_at']),
        ]

    def __str__(self):
        return f'{self.query} @ {self.created_at:%Y-%m-%d %H:%M}'
