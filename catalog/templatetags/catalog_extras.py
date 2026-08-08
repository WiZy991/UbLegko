from urllib.parse import urlencode

from django import template

register = template.Library()

_FILTER_KEYS = ('in_stock', 'promo', 'price', 'sort', 'q', 'page')


@register.simple_tag(takes_context=True)
def catalog_query(context, **updates):
    """Build ?query for catalog links; pass empty string to drop a param."""
    request = context.get('request')
    params = {}
    if request is not None:
        for key in _FILTER_KEYS:
            value = request.GET.get(key)
            if value not in (None, ''):
                params[key] = value

    for key, value in updates.items():
        if value is None or value == '':
            params.pop(key, None)
        else:
            params[key] = str(value)

    # Changing filters/sort resets pagination unless page is explicitly set.
    if 'page' not in updates:
        params.pop('page', None)

    query = urlencode(params)
    return f'?{query}' if query else '?'


@register.simple_tag(takes_context=True)
def catalog_clear_filters(context):
    """Keep only sort and search query."""
    request = context.get('request')
    params = {}
    if request is not None:
        sort = request.GET.get('sort')
        q = request.GET.get('q')
        if sort:
            params['sort'] = sort
        if q:
            params['q'] = q
    query = urlencode(params)
    return f'?{query}' if query else '?'
