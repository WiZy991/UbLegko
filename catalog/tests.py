from django.test import SimpleTestCase, TestCase

from catalog.models import Category, Product
from catalog.search_utils import (
    build_product_search_text,
    filter_products_by_query,
    query_variants,
    rank_prefix_first,
    stem_variants,
    text_search_q,
)
from catalog.seo_keywords import matches_stain_help_query


class SearchUtilsTests(SimpleTestCase):
    def test_stem_variants_russian_plural(self):
        stems = stem_variants('пятновыводитель')
        self.assertIn('пятновыводитель', stems)
        self.assertIn('пятновыводител', stems)

    def test_matches_stain_help_query_prefixes(self):
        self.assertTrue(matches_stain_help_query('чем отмыть жир'))
        self.assertTrue(matches_stain_help_query('как смыть накипь'))
        self.assertTrue(matches_stain_help_query('чем отстирать кровь'))
        self.assertFalse(matches_stain_help_query('моющие средства купить'))
        self.assertFalse(matches_stain_help_query('Amol'))

    def test_text_search_q_matches_description_stem(self):
        q_obj = text_search_q('пятновыводитель')
        sql = str(q_obj)
        self.assertIn('search_text', sql)
        self.assertIn('пятновыводител', sql)

    def test_build_product_search_text_casefold(self):
        text = build_product_search_text(
            name='Пятновыводитель Pro',
            description='Для КОВРОВ',
        )
        self.assertIn('пятновыводитель pro', text)
        self.assertIn('для ковров', text)
        self.assertEqual(text, text.casefold())

    def test_build_product_search_text_excludes_seo_phrases(self):
        text = build_product_search_text(
            name='Жидкое мыло',
            description='Для рук',
            category_name='Мыло',
        )
        self.assertIn('жидкое мыло', text)
        self.assertIn('для рук', text)
        # SEO-фразы больше не попадают в индекс — иначе «для пола» находило весь каталог
        self.assertNotIn('купить средство для пола', text)
        self.assertNotIn('приморский край', text)

    def test_query_variants_layout(self):
        variants = query_variants('vfkm')
        self.assertTrue(any('мал' in v for v in variants))

    def test_rank_prefix_first_description_after_name(self):
        class P:
            def __init__(self, name, description=''):
                self.name = name
                self.description = description

        products = [
            P('CLF 1л', description='пятновыводители для ковров'),
            P('Пятновыводитель Pro', description=''),
        ]
        ranked = rank_prefix_first(products, 'пятновыводитель')
        self.assertEqual(ranked[0].name, 'Пятновыводитель Pro')


class ProductSlugTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Тест', slug='test-cat')

    def test_cyrillic_slug_saves_on_resave(self):
        product = Product.objects.create(
            name='Alfa 20 1л',
            slug='alfa-20-1л',
            category=self.category,
            price='100.00',
        )
        product.description = 'Обновление при загрузке фото'
        product.save()
        product.refresh_from_db()
        self.assertEqual(product.slug, 'alfa-20-1л')

    def test_slug_normalized_on_save(self):
        product = Product(
            name='Тестовый товар',
            slug='Тест 1 л',
            category=self.category,
            price='50.00',
        )
        product.save()
        self.assertEqual(product.slug, 'тест-1-л')


class SearchCaseInsensitivityTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name='Чистящие', slug='cleaners')
        self.product = Product.objects.create(
            name='CLF 1л',
            category=category,
            price='100.00',
            description='Эффективные пятновыводители для ковров',
        )

    def test_uppercase_query_finds_product(self):
        qs = Product.objects.filter(is_visible=True)
        found = filter_products_by_query(qs, 'ПЯТНОВЫВОДИТЕЛЬ')
        self.assertIn(self.product, list(found))

    def test_capitalized_query_finds_product(self):
        qs = Product.objects.filter(is_visible=True)
        found = filter_products_by_query(qs, 'Пятновыводитель')
        self.assertIn(self.product, list(found))


class SearchRelevanceTests(TestCase):
    def setUp(self):
        floor_cat = Category.objects.create(name='Общая уборка', slug='floor-cat')
        soap_cat = Category.objects.create(name='Мыло', slug='soap-cat')
        self.floor = Product.objects.create(
            name='Concentrate Floor',
            category=floor_cat,
            price='100.00',
            description='Средство для пола и твёрдых поверхностей',
        )
        self.soap = Product.objects.create(
            name='Жидкое мыло',
            category=soap_cat,
            price='50.00',
            description='Мыло для рук и тела',
        )

    def test_dlya_pola_does_not_match_soap(self):
        qs = Product.objects.filter(is_visible=True)
        found = list(filter_products_by_query(qs, 'для пола'))
        self.assertIn(self.floor, found)
        self.assertNotIn(self.soap, found)

    def test_pola_not_inside_opolaskivatel(self):
        cat = Category.objects.create(name='Посуда', slug='dish-cat')
        rinse = Product.objects.create(
            name='Rinse',
            category=cat,
            price='10.00',
            description='Ополаскиватель для машинной мойки',
        )
        qs = Product.objects.filter(is_visible=True)
        found = list(filter_products_by_query(qs, 'для пола'))
        self.assertNotIn(rinse, found)
