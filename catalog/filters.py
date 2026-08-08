from decimal import Decimal


PRICE_PRESETS = (
    {
        'key': '0-500',
        'label': 'До 500 ₽',
        'min': Decimal('0'),
        'max': Decimal('500'),
    },
    {
        'key': '500-1500',
        'label': '500–1500 ₽',
        'min': Decimal('500'),
        'max': Decimal('1500'),
    },
    {
        'key': '1500-3000',
        'label': '1500–3000 ₽',
        'min': Decimal('1500'),
        'max': Decimal('3000'),
    },
    {
        'key': '3000+',
        'label': 'От 3000 ₽',
        'min': Decimal('3000'),
        'max': None,
    },
)

PRICE_PRESET_MAP = {item['key']: item for item in PRICE_PRESETS}


def parse_catalog_filters(params) -> dict:
    in_stock = params.get('in_stock') in ('1', 'true', 'yes', 'on')
    promo = params.get('promo') in ('1', 'true', 'yes', 'on')
    price_key = (params.get('price') or '').strip()
    if price_key not in PRICE_PRESET_MAP:
        price_key = ''
    return {
        'in_stock': in_stock,
        'promo': promo,
        'price': price_key,
    }


def has_active_filters(filters: dict) -> bool:
    return bool(filters.get('in_stock') or filters.get('promo') or filters.get('price'))


def apply_catalog_filters(qs, filters: dict):
    if filters.get('in_stock'):
        qs = qs.filter(status='in_stock')
    if filters.get('promo'):
        qs = qs.filter(is_promo=True)
    price_key = filters.get('price') or ''
    preset = PRICE_PRESET_MAP.get(price_key)
    if preset:
        qs = qs.filter(price__gte=preset['min'])
        if preset['max'] is not None:
            qs = qs.filter(price__lte=preset['max'])
    return qs
