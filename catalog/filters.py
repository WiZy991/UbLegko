from decimal import Decimal


def parse_catalog_filters(params) -> dict:
    in_stock = params.get('in_stock') in ('1', 'true', 'yes', 'on')
    promo = params.get('promo') in ('1', 'true', 'yes', 'on')
    is_new = params.get('new') in ('1', 'true', 'yes', 'on')
    return {
        'in_stock': in_stock,
        'promo': promo,
        'new': is_new,
        'price': '',
    }


def has_active_filters(filters: dict, sort: str | None = None) -> bool:
    """Сбросить — после любого фильтра или сортировки ≠ «По категориям»."""
    if filters.get("in_stock") or filters.get("promo") or filters.get("new"):
        return True
    if sort and sort != "category":
        return True
    return False


def apply_catalog_filters(qs, filters: dict):
    if filters.get('in_stock'):
        qs = qs.filter(status='in_stock')
    if filters.get('promo'):
        qs = qs.filter(is_promo=True)
    if filters.get('new'):
        qs = qs.filter(is_new=True)
    return qs
