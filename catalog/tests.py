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
        self.assertEqual(text, 'пятновыводитель pro для ковров')

    def test_build_product_search_text_includes_seo_phrases(self):
        text = build_product_search_text(
            name='Средство для пола',
            category_name='Общая уборка',
        )
        self.assertIn('чем отмыть жир', text)
        self.assertIn('приморский край', text)

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
