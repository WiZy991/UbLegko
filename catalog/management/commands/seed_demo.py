from decimal import Decimal

from django.core.management.base import BaseCommand

from catalog.models import Category, Product, ProductRecommendation
from core.models import City, SiteSettings


CATEGORIES = [
    'Общая уборка',
    'Химчистка',
    'Для стирки',
    'Для посудомоечных машин',
    'Пищевое производство',
    'Освежители и поглотители',
    'Мыло',
    'Антисептики',
    'Сопутствующие товары',
    'Для машины',
    'Масла и смазки',
    'Деревообработка',
    'Услуги',
]

PRODUCTS = [
    {
        'name': 'Amol 0,5 л',
        'category': 'Общая уборка',
        'short_description': 'Антижир последнего поколения, эффективно моет и чистит ско...',
        'description': 'Профессиональное средство Amol для удаления жировых загрязнений на кухне и в пищевом производстве.',
        'price': Decimal('650'),
        'is_promo': True,
        'is_featured': True,
        'rating': Decimal('4.9'),
    },
    {
        'name': 'Pro-Brite Universal 1 л',
        'category': 'Общая уборка',
        'short_description': 'Универсальное моющее средство для ежедневной уборки.',
        'description': 'Подходит для пола, стен и твёрдых поверхностей.',
        'price': Decimal('490'),
        'is_promo': False,
        'is_featured': True,
        'rating': Decimal('4.8'),
    },
    {
        'name': 'Carpet Clean 1 л',
        'category': 'Химчистка',
        'short_description': 'Шампунь для химчистки ковров и мягкой мебели.',
        'description': 'Удаляет пятна и неприятные запахи, подходит для экстракторной чистки.',
        'price': Decimal('780'),
        'is_promo': True,
        'is_featured': False,
        'rating': Decimal('4.7'),
    },
    {
        'name': 'Wash Soft 5 л',
        'category': 'Для стирки',
        'short_description': 'Жидкое средство для стирки белья.',
        'description': 'Эффективно при низких температурах, подходит для цветного и белого белья.',
        'price': Decimal('1200'),
        'is_promo': False,
        'is_featured': False,
        'rating': Decimal('4.6'),
    },
    {
        'name': 'Dish Pro 5 л',
        'category': 'Для посудомоечных машин',
        'short_description': 'Средство для профессиональных посудомоечных машин.',
        'description': 'Предотвращает образование налёта и обеспечивает блеск посуды.',
        'price': Decimal('1450'),
        'is_promo': False,
        'is_featured': True,
        'rating': Decimal('4.8'),
    },
    {
        'name': 'Sanit Gel 0,5 л',
        'category': 'Антисептики',
        'short_description': 'Антисептический гель для рук.',
        'description': 'Быстро испаряется, не требует смывания.',
        'price': Decimal('320'),
        'is_promo': True,
        'is_featured': False,
        'rating': Decimal('4.5'),
    },
]


class Command(BaseCommand):
    help = 'Создаёт демо-категории, товары и настройки сайта'

    def handle(self, *args, **options):
        SiteSettings.load()
        # Города России — отдельной командой seed_cities; здесь только default
        City.objects.filter(name='Уссурийск').update(is_default=True)
        City.objects.exclude(name='Уссурийск').update(is_default=False)
        categories = {}
        for i, name in enumerate(CATEGORIES):
            cat, _ = Category.objects.get_or_create(
                name=name,
                defaults={'sort_order': i * 10, 'is_visible': True},
            )
            categories[name] = cat

        products = {}
        for data in PRODUCTS:
            category = categories[data['category']]
            product, created = Product.objects.update_or_create(
                name=data['name'],
                category=category,
                defaults={
                    'short_description': data['short_description'],
                    'description': data['description'],
                    'price': data['price'],
                    'is_promo': data['is_promo'],
                    'is_featured': data['is_featured'],
                    'rating': data['rating'],
                    'status': Product.Status.IN_STOCK,
                    'is_visible': True,
                },
            )
            products[data['name']] = product
            self.stdout.write(('+' if created else '~') + f' {product.name}')

        amol = products['Amol 0,5 л']
        for name in ['Pro-Brite Universal 1 л', 'Sanit Gel 0,5 л', 'Dish Pro 5 л']:
            ProductRecommendation.objects.get_or_create(
                product=amol,
                recommended_product=products[name],
            )

        self.stdout.write(self.style.SUCCESS('Демо-данные загружены'))
        self.stdout.write('Для импортированного каталога выполните: python manage.py seed_recommendations')
