from django.core.validators import MaxValueValidator, MinValueValidator
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


TICKER_FONT_CHOICES = [
    ('manrope', 'Manrope'),
    ('arial', 'Arial'),
    ('arialblack', 'Arial Black'),
    ('verdana', 'Verdana'),
    ('tahoma', 'Tahoma'),
    ('segoe', 'Segoe UI'),
    ('trebuchet', 'Trebuchet MS'),
    ('georgia', 'Georgia'),
    ('times', 'Times New Roman'),
    ('courier', 'Courier New'),
    ('impact', 'Impact'),
    ('oswald', 'Oswald'),
    ('rubik', 'Rubik'),
    ('montserrat', 'Montserrat'),
    ('playfair', 'Playfair Display'),
    ('comfortaa', 'Comfortaa'),
    ('russo', 'Russo One'),
    ('ptserif', 'PT Serif'),
]

TICKER_FONT_FAMILY = {
    'manrope': '"Manrope", sans-serif',
    'arial': 'Arial, Helvetica, sans-serif',
    'arialblack': '"Arial Black", "Arial Bold", Gadget, sans-serif',
    'verdana': 'Verdana, Geneva, sans-serif',
    'tahoma': 'Tahoma, Geneva, sans-serif',
    'segoe': '"Segoe UI", sans-serif',
    'trebuchet': '"Trebuchet MS", sans-serif',
    'georgia': 'Georgia, serif',
    'times': '"Times New Roman", Times, serif',
    'courier': '"Courier New", Courier, monospace',
    'impact': 'Impact, Haettenschweiler, sans-serif',
    'oswald': '"Oswald", sans-serif',
    'rubik': '"Rubik", sans-serif',
    'montserrat': '"Montserrat", sans-serif',
    'playfair': '"Playfair Display", Georgia, serif',
    'comfortaa': '"Comfortaa", sans-serif',
    'russo': '"Russo One", sans-serif',
    'ptserif': '"PT Serif", Georgia, serif',
}

TICKER_FONT_GOOGLE = {
    'oswald': 'https://fonts.googleapis.com/css2?family=Oswald:wght@700&display=swap',
    'rubik': 'https://fonts.googleapis.com/css2?family=Rubik:wght@700&display=swap',
    'montserrat': 'https://fonts.googleapis.com/css2?family=Montserrat:wght@700&display=swap',
    'playfair': 'https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&display=swap',
    'comfortaa': 'https://fonts.googleapis.com/css2?family=Comfortaa:wght@700&display=swap',
    'russo': 'https://fonts.googleapis.com/css2?family=Russo+One&display=swap',
    'ptserif': 'https://fonts.googleapis.com/css2?family=PT+Serif:wght@700&display=swap',
}


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
    ddos_rate_limit_hits = models.PositiveIntegerField(
        'DDoS: хитов',
        default=15,
        help_text='Сколько запросов с одного IP за окно времени — и IP блокируется на 1 час.',
    )
    ddos_rate_window_seconds = models.PositiveIntegerField(
        'DDoS: секунд',
        default=10,
        help_text='Окно времени в секундах для подсчёта хитов.',
    )
    ticker_text = models.TextField(
        'Текст',
        blank=True,
        default='',
        help_text='Если поле пустое, строка на сайте не показывается.',
    )
    ticker_font = models.CharField(
        'Шрифт',
        max_length=32,
        choices=TICKER_FONT_CHOICES,
        default='manrope',
    )
    ticker_font_size = models.PositiveSmallIntegerField(
        'Размер шрифта',
        default=32,
        validators=[MinValueValidator(12), MaxValueValidator(72)],
        help_text='Размер на компьютере, в пикселях. На телефоне шрифт остаётся небольшим.',
    )
    ticker_speed_seconds = models.PositiveSmallIntegerField(
        'Скорость, секунд',
        default=18,
        validators=[MinValueValidator(4), MaxValueValidator(1000)],
        help_text=(
            'Сколько секунд весь написанный текст едет один круг. '
            'От 4 до 1000. Чем больше число, тем медленнее.'
        ),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Настройки сайта'
        verbose_name_plural = 'Настройки сайта'

    def __str__(self):
        return 'Настройки сайта'

    @property
    def ticker_line(self):
        return ' '.join((self.ticker_text or '').split())

    @property
    def ticker_seconds(self):
        try:
            seconds = int(self.ticker_speed_seconds)
        except (TypeError, ValueError):
            seconds = 18
        return min(1000, max(4, seconds))

    @property
    def ticker_font_size_px(self):
        try:
            size = int(self.ticker_font_size)
        except (TypeError, ValueError):
            size = 32
        return min(72, max(12, size))

    @property
    def ticker_font_family(self):
        return TICKER_FONT_FAMILY.get(self.ticker_font, TICKER_FONT_FAMILY['manrope'])

    @property
    def ticker_google_font_href(self):
        return TICKER_FONT_GOOGLE.get(self.ticker_font, '')

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SiteVisit(models.Model):
    """Один логический заход: один IP в окне 5 минут (фриз-тайм)."""

    visitor_key = models.CharField('Посетитель', max_length=64, db_index=True)
    ip_address = models.GenericIPAddressField('IP', null=True, blank=True, db_index=True)
    geo_country = models.CharField('Страна', max_length=80, blank=True)
    geo_region = models.CharField('Регион', max_length=120, blank=True)
    geo_city = models.CharField('Город', max_length=120, blank=True)
    device = models.CharField('Устройство', max_length=120, blank=True)
    path = models.CharField('Страница', max_length=300, blank=True)
    hit_count = models.PositiveIntegerField('Хитов за 5 мин', default=1)
    visited_at = models.DateTimeField('Начало захода', auto_now_add=True, db_index=True)
    last_hit_at = models.DateTimeField('Последний хит', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Заход на сайт'
        verbose_name_plural = 'Заходы на сайт'
        indexes = [
            models.Index(fields=['visited_at']),
            models.Index(fields=['visitor_key', 'visited_at']),
            models.Index(fields=['ip_address', 'visited_at']),
        ]

    def __str__(self):
        return f'{self.path or "/"} @ {self.visited_at:%Y-%m-%d %H:%M}'


class SitePresence(models.Model):
    """Открытая витрина. Телефон и компьютер считаются по отдельности."""

    presence_key = models.CharField('Браузер', max_length=64, unique=True)
    last_seen_at = models.DateTimeField('Последний сигнал', db_index=True)

    class Meta:
        verbose_name = 'Сейчас на сайте'
        verbose_name_plural = 'Сейчас на сайте'

    def __str__(self):
        return f'{self.presence_key} @ {self.last_seen_at:%H:%M:%S}'


class BlockedIP(models.Model):
    """Блокировка IP: на час при DDoS или вручную до снятия."""

    ip_address = models.GenericIPAddressField('IP', primary_key=True)
    blocked_until = models.DateTimeField('Заблокирован до', db_index=True)
    is_manual = models.BooleanField('Вручную', default=False)
    created_at = models.DateTimeField('Когда', auto_now_add=True)

    class Meta:
        verbose_name = 'Заблокированный IP'
        verbose_name_plural = 'Заблокированные IP'

    def __str__(self):
        return f'{self.ip_address} до {self.blocked_until:%d.%m.%Y %H:%M}'


class IPRateHit(models.Model):
    """Счётчик запросов для анти-DDoS (скользящее окно 10 сек)."""

    ip_address = models.GenericIPAddressField('IP', db_index=True)
    hit_at = models.DateTimeField('Когда', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Хит IP'
        verbose_name_plural = 'Хиты IP'
        indexes = [
            models.Index(fields=['ip_address', 'hit_at']),
        ]


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
