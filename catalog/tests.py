from django.test import SimpleTestCase

from catalog.search_utils import (
    filter_products_by_query,
    query_variants,
    rank_prefix_first,
    stem_variants,
    text_search_q,
)


class SearchUtilsTests(SimpleTestCase):
    def test_stem_variants_russian_plural(self):
        stems = stem_variants('пятновыводитель')
        self.assertIn('пятновыводитель', stems)
        self.assertIn('пятновыводител', stems)

    def test_text_search_q_matches_description_stem(self):
        q_obj = text_search_q('пятновыводитель')
        sql = str(q_obj)
        self.assertIn('description', sql)
        self.assertIn('short_description', sql)
        self.assertIn('пятновыводител', sql)

    def test_query_variants_layout(self):
        variants = query_variants('vfkm')
        self.assertTrue(any('мал' in v for v in variants))

    def test_rank_prefix_first_description_after_name(self):
        class P:
            def __init__(self, name, short_description='', description=''):
                self.name = name
                self.short_description = short_description
                self.description = description

        products = [
            P('CLF 1л', description='пятновыводители для ковров'),
            P('Пятновыводитель Pro', short_description=''),
        ]
        ranked = rank_prefix_first(products, 'пятновыводитель')
        self.assertEqual(ranked[0].name, 'Пятновыводитель Pro')
