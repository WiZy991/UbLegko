"""Ценники: список товаров в админке и печать обычного или акционного шаблона."""

import json
import re
from decimal import Decimal, InvalidOperation

from django.core.paginator import Paginator
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone
from django.utils.html import escape, strip_tags
from django.utils.safestring import mark_safe

from core.models import SiteSettings

from .models import Product

COMPANY_NAME = 'ООО СОЛНЕЧНЫЙ МЕЧ'
PAGE_SIZE = 50
TAG_WIDTH_CM = '5,8'
TAG_HEIGHT_CM = '3,8'

_EAN_L = {
    '0': '0001101', '1': '0011001', '2': '0010011', '3': '0111101', '4': '0100011',
    '5': '0110001', '6': '0101111', '7': '0111011', '8': '0110111', '9': '0001011',
}
_EAN_G = {
    '0': '0100111', '1': '0110011', '2': '0011011', '3': '0100001', '4': '0011101',
    '5': '0111001', '6': '0000101', '7': '0010001', '8': '0001001', '9': '0010111',
}
_EAN_R = {
    '0': '1110010', '1': '1100110', '2': '1101100', '3': '1000010', '4': '1011100',
    '5': '1001110', '6': '1010000', '7': '1000100', '8': '1001000', '9': '1110100',
}
_EAN_PARITY = {
    '0': 'LLLLLL', '1': 'LLGLGG', '2': 'LLGGLG', '3': 'LLGGGL', '4': 'LGLLGG',
    '5': 'LGGLLG', '6': 'LGGGLL', '7': 'LGLGLG', '8': 'LGLGGL', '9': 'LGGLGL',
}


def _digits(value: str) -> str:
    return re.sub(r'\D', '', value or '')


def _ean_checksum(body: str) -> str:
    total = 0
    for index, char in enumerate(body):
        total += int(char) * (1 if index % 2 == 0 else 3)
    return str((10 - (total % 10)) % 10)


def _ean13_bits(number: str) -> str | None:
    digits = _digits(number)
    if len(digits) == 12:
        digits += _ean_checksum(digits)
    if len(digits) != 13 or digits[-1] != _ean_checksum(digits[:12]):
        return None
    bits = '101'
    parity = _EAN_PARITY[digits[0]]
    for index, flag in enumerate(parity):
        table = _EAN_L if flag == 'L' else _EAN_G
        bits += table[digits[index + 1]]
    bits += '01010'
    for char in digits[7:]:
        bits += _EAN_R[char]
    bits += '101'
    return bits


def barcode_svg(number: str) -> str:
    bits = _ean13_bits(number)
    if not bits:
        return ''
    module = 1
    height = 32
    width = len(bits) * module
    bars = []
    x = 0
    while x < len(bits):
        if bits[x] == '1':
            start = x
            while x < len(bits) and bits[x] == '1':
                x += 1
            bars.append(
                f'<rect x="{start * module}" y="0" width="{(x - start) * module}" height="{height}" fill="#111"/>'
            )
        else:
            x += 1
    svg = (
        f'<svg class="tag__barcode" viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="none" role="img" aria-label="{escape(number)}">'
        f'{"".join(bars)}</svg>'
    )
    return mark_safe(svg)


def _price_parts(value) -> tuple[str, str]:
    if value is None:
        return '', ''
    amount = Decimal(value).quantize(Decimal('0.01'))
    rubles = int(amount)
    kopecks = int((amount - rubles) * 100)
    return str(rubles), f'{kopecks:02d}'


def _input_amount(value) -> str:
    if value is None:
        return ''
    amount = Decimal(value).quantize(Decimal('0.01'))
    text = f'{amount:.2f}'
    if text.endswith('.00'):
        return text[:-3]
    return text


def _parse_money(raw):
    text = str(raw or '').replace('\u00a0', '').replace(' ', '').replace(',', '.').strip()
    if not text:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, TypeError, ValueError):
        return None


def is_promo_price(product: Product) -> bool:
    return product.old_price is not None and product.old_price > 0


def tag_description(product: Product) -> str:
    raw = (product.price_tag_description or '').strip() or (product.description or '').strip()
    return ' '.join(strip_tags(raw).replace('\xa0', ' ').split())


def tag_context(product: Product, printed_on: str, company: str) -> dict:
    rubles, kopecks = _price_parts(product.price)
    old_rubles, old_kopecks = _price_parts(product.old_price if is_promo_price(product) else None)
    unit = (product.unit or '').strip() or 'шт'
    return {
        'name': product.name,
        'description': tag_description(product),
        'sku': product.sku or '',
        'barcode': product.barcode or '',
        'barcode_svg': barcode_svg(product.barcode or ''),
        'rubles': rubles,
        'kopecks': kopecks,
        'old_rubles': old_rubles,
        'old_kopecks': old_kopecks,
        'promo': is_promo_price(product),
        'unit': unit,
        'country': product.country or '',
        'company': company,
        'printed_on': printed_on,
    }


def _company_name() -> str:
    try:
        name = (SiteSettings.load().company_name or '').strip()
    except Exception:  # noqa: BLE001
        name = ''
    return name or COMPANY_NAME


def _printed_on() -> str:
    return timezone.localdate().strftime('%d.%m.%Y') + ' г.'


def render_price_tags(request):
    query = (request.GET.get('q') or '').strip()
    products = Product.objects.select_related('category').order_by('name')
    if query:
        products = products.filter(name__icontains=query)
    paginator = Paginator(products, PAGE_SIZE)
    page = paginator.get_page(request.GET.get('page') or 1)
    rows = []
    for product in page.object_list:
        rows.append({
            'product': product,
            'promo': is_promo_price(product),
            'description': tag_description(product),
            'price_input': _input_amount(product.price),
            'old_price_input': _input_amount(product.old_price),
        })
    return render(request, 'admin/catalog/price_tags.html', {
        'title': 'Ценники',
        'printed_on': _printed_on(),
        'company': _company_name(),
        'page': page,
        'rows': rows,
        'query': query,
        'tag_width_cm': TAG_WIDTH_CM,
        'tag_height_cm': TAG_HEIGHT_CM,
        'sample_regular': _sample_tag(False),
        'sample_promo': _sample_tag(True),
    })


def _sample_tag(promo: bool) -> dict:
    return {
        'name': 'Название Вашего Продукта',
        'description': 'Описание Вашего продукта',
        'sku': '1234567890',
        'barcode': '4600000000008',
        'barcode_svg': barcode_svg('4600000000008'),
        'rubles': '299',
        'kopecks': '95',
        'old_rubles': '500' if promo else '',
        'old_kopecks': '00' if promo else '',
        'promo': promo,
        'unit': 'шт',
        'country': 'Россия',
        'company': COMPANY_NAME,
        'printed_on': '01.02.2023 г.',
    }


def _posted_items(request) -> list[dict]:
    raw = request.POST.get('items') or ''
    if raw:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = []
        if isinstance(data, list):
            items = []
            for item in data:
                if isinstance(item, dict) and item.get('id') not in (None, ''):
                    items.append(item)
            if items:
                return items
    items = []
    for raw_id in request.POST.getlist('ids'):
        try:
            items.append({'id': int(raw_id)})
        except (TypeError, ValueError):
            continue
    return items


def _tag_copies(item: dict, product: Product, printed_on: str, company: str) -> list[dict]:
    try:
        qty = int(item.get('qty') or 1)
    except (TypeError, ValueError):
        qty = 1
    qty = min(99, max(1, qty))
    if set(item.keys()) <= {'id', 'qty'}:
        tag = tag_context(product, printed_on, company)
        return [tag for _ in range(qty)]
    price = _parse_money(item.get('price'))
    if price is None:
        price = product.price
    old_price = _parse_money(item.get('old_price')) if 'old_price' in item else product.old_price
    promo = old_price is not None and old_price > 0
    rubles, kopecks = _price_parts(price)
    old_rubles, old_kopecks = _price_parts(old_price if promo else None)
    barcode = str(item.get('barcode') if 'barcode' in item else product.barcode or '').strip()
    description = str(item.get('description') if 'description' in item else tag_description(product))
    description = ' '.join(strip_tags(description).replace('\xa0', ' ').split())
    unit = str(item.get('unit') if 'unit' in item else product.unit or '').strip() or 'шт'
    tag = {
        'name': str(item.get('name') if 'name' in item else product.name).strip() or product.name,
        'description': description,
        'sku': str(item.get('sku') if 'sku' in item else product.sku or '').strip(),
        'barcode': barcode,
        'barcode_svg': barcode_svg(barcode),
        'rubles': rubles,
        'kopecks': kopecks,
        'old_rubles': old_rubles,
        'old_kopecks': old_kopecks,
        'promo': promo,
        'unit': unit,
        'country': str(item.get('country') if 'country' in item else product.country or '').strip(),
        'company': company,
        'printed_on': printed_on,
    }
    return [tag for _ in range(qty)]


def render_price_tags_print(request, products=None):
    if request.method != 'POST':
        return HttpResponseForbidden('Отметьте товары и нажмите печать.')
    printed_on = _printed_on()
    company = _company_name()
    if products is not None:
        tags = [tag_context(product, printed_on, company) for product in products]
    else:
        items = _posted_items(request)
        ids = []
        for item in items:
            try:
                ids.append(int(item.get('id')))
            except (TypeError, ValueError):
                continue
        found = {product.pk: product for product in Product.objects.filter(pk__in=ids)}
        tags = []
        for item in items:
            try:
                product = found.get(int(item.get('id')))
            except (TypeError, ValueError):
                product = None
            if product is None:
                continue
            tags.extend(_tag_copies(item, product, printed_on, company))
    return render(request, 'admin/catalog/price_tags_print.html', {
        'title': 'Ценники',
        'tags': tags,
        'tag_width_cm': TAG_WIDTH_CM,
        'tag_height_cm': TAG_HEIGHT_CM,
    })
