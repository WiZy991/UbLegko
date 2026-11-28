"""PDF-лист ценников в тех же миллиметрах, что и страница печати."""

from pathlib import Path

from django.http import HttpResponse
from fpdf import FPDF

from .price_tags import _ean13_bits

_FONT_DIR = Path(__file__).resolve().parent.parent / 'static' / 'admin' / 'fonts' / 'ttf'

TAG_W = 58.0
TAG_H = 38.0
PAD_X = 1.3
PAD_T = 1.1
PAD_B = 0.7
PAGE_X = 9.8
PAGE_Y = 9.8
GAP = 0.5
COLS = 3
ROWS = 7
BARCODE_W = 26.0
BARCODE_H = 4.0
BADGE_W = 22.0
BADGE_H = 6.2
PRICE_H = 9.0


def _pt(points: float) -> float:
    return points * 25.4 / 72.0


def _lines(pdf, text: str, width: float, max_lines: int) -> list[str]:
    words = (text or '').split()
    if not words or max_lines <= 0 or width <= 1:
        return []
    lines: list[str] = []
    current = ''
    for word in words:
        if pdf.get_string_width(word) > width:
            if current:
                lines.append(current)
                current = ''
                if len(lines) >= max_lines:
                    break
            chunk = ''
            for char in word:
                if pdf.get_string_width(chunk + char) <= width:
                    chunk += char
                    continue
                if chunk:
                    lines.append(chunk)
                chunk = char
                if len(lines) >= max_lines:
                    chunk = ''
                    break
            current = chunk
            if len(lines) >= max_lines:
                break
            continue
        trial = word if not current else f'{current} {word}'
        if pdf.get_string_width(trial) <= width:
            current = trial
            continue
        lines.append(current)
        current = word
        if len(lines) >= max_lines:
            current = ''
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    return lines


def _write(pdf, x, y, width, height, text, align='L'):
    pdf.set_xy(x, y)
    pdf.cell(width, height, text or '', align=align)


def _prepare(pdf: FPDF) -> None:
    pdf.add_font('Roboto', '', str(_FONT_DIR / 'roboto-regular.ttf'))
    pdf.add_font('Roboto', 'B', str(_FONT_DIR / 'roboto-bold.ttf'))
    pdf.add_font('Fjalla', '', str(_FONT_DIR / 'fjalla.ttf'))
    pdf.add_font('PTSans', 'B', str(_FONT_DIR / 'ptsans-bold.ttf'))
    pdf.set_auto_page_break(False)
    pdf.set_margin(0)


def _draw_badge(pdf, x, y):
    raw = ((0, 0), (122, 0), (148, 21), (122, 42), (0, 42))
    points = [(x + px / 148 * BADGE_W, y + py / 42 * BADGE_H) for px, py in raw]
    pdf.set_fill_color(225, 6, 0)
    pdf.polygon(points, style='F')
    label = 'АКЦИЯ!'
    pdf.set_font('PTSans', 'B', 16)
    pdf.set_text_color(255, 225, 0)
    body_w = BADGE_W * 122 / 148
    text_w = pdf.get_string_width(label)
    pdf.set_xy(x + max(0.4, (body_w - text_w) / 2), y + (BADGE_H - _pt(16)) / 2)
    pdf.cell(text_w, _pt(16), label)
    pdf.set_text_color(0, 0, 0)


def _draw_price(pdf, left, right, top, tag):
    rubles = str(tag.get('rubles') or '0')
    kopecks = str(tag.get('kopecks') or '00')
    rub_size = 20 if len(rubles) >= 5 else 30
    pdf.set_font('Fjalla', '', 11)
    kop_w = max(4.6, pdf.get_string_width(kopecks) + 0.3)
    pdf.set_font('Roboto', '', 7.5)
    col_w = max(kop_w, pdf.get_string_width('руб.'))
    pdf.set_char_spacing(-0.03 * _pt(rub_size))
    pdf.set_font('Fjalla', '', rub_size)
    rub_w = pdf.get_string_width(rubles)
    pdf.set_char_spacing(0)
    block_w = rub_w + 0.35 + col_w
    block_x = max(left, right - block_w)
    pdf.set_char_spacing(-0.03 * _pt(rub_size))
    pdf.set_font('Fjalla', '', rub_size)
    _write(pdf, block_x, top, rub_w, _pt(rub_size) * 0.8, rubles)
    pdf.set_char_spacing(0)
    kop_x = block_x + rub_w + 0.35
    pdf.set_font('Fjalla', '', 11)
    _write(pdf, kop_x, top + 0.15, col_w, _pt(11) * 0.9, kopecks, align='C')
    line_y = top + 0.15 + _pt(11) * 0.92
    pdf.set_draw_color(17, 17, 17)
    pdf.set_line_width(0.28)
    pdf.line(kop_x + (col_w - kop_w) / 2, line_y, kop_x + (col_w + kop_w) / 2, line_y)
    pdf.set_font('Roboto', '', 7.5)
    _write(pdf, kop_x, line_y + 0.2, col_w, _pt(7.5) * 1.05, 'руб.', align='C')


def _draw_old_price(pdf, right, top, tag) -> float:
    pdf.set_font('Roboto', '', 5.2)
    label_w = max(13.5, pdf.get_string_width('Старая цена:'))
    _write(pdf, right - label_w, top, label_w, _pt(5.2) * 1.1, 'Старая цена:', align='R')
    y = top + _pt(5.2) * 1.2
    old_rubles = str(tag.get('old_rubles') or '')
    old_kopecks = str(tag.get('old_kopecks') or '')
    pdf.set_font('Fjalla', '', 10)
    rub_w = pdf.get_string_width(old_rubles)
    pdf.set_font('Fjalla', '', 5.5)
    kop_w = pdf.get_string_width(old_kopecks)
    total = rub_w + kop_w
    x = right - total
    pdf.set_font('Fjalla', '', 10)
    _write(pdf, x, y, rub_w, _pt(10) * 0.9, old_rubles)
    pdf.set_font('Fjalla', '', 5.5)
    _write(pdf, x + rub_w, y + 0.15, kop_w, _pt(5.5), old_kopecks)
    pdf.set_draw_color(225, 6, 0)
    pdf.set_line_width(0.32)
    strike_y = y + _pt(10) * 0.5
    pdf.line(x - 0.3, strike_y + 0.4, x + total + 0.35, strike_y - 0.35)
    pdf.set_draw_color(17, 17, 17)
    y2 = y + _pt(10) * 0.95
    pdf.set_font('Roboto', '', 4.5)
    _write(pdf, right - label_w, y2, label_w, _pt(4.5), 'руб.', align='R')
    return label_w


def _draw_barcode(pdf, x, y, bits: str):
    pdf.set_fill_color(17, 17, 17)
    module = BARCODE_W / len(bits)
    index = 0
    while index < len(bits):
        if bits[index] != '1':
            index += 1
            continue
        start = index
        while index < len(bits) and bits[index] == '1':
            index += 1
        pdf.rect(x + start * module, y, (index - start) * module, BARCODE_H, style='F')


def _draw_tag(pdf, ox, oy, tag: dict):
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(ox, oy, TAG_W, TAG_H, style='F')
    pdf.set_draw_color(34, 34, 34)
    pdf.set_line_width(0.2)
    pdf.set_dash_pattern(dash=0.35, gap=0.35)
    pdf.rect(ox, oy, TAG_W, TAG_H)
    pdf.set_dash_pattern(0)
    pdf.set_text_color(0, 0, 0)

    left = ox + PAD_X
    right = ox + TAG_W - PAD_X
    inner_w = right - left
    bottom = oy + TAG_H - PAD_B
    bits = _ean13_bits(tag.get('barcode') or '')
    foot_h = _pt(5.4) * 1.15 + (0.25 + BARCODE_H if bits else 0)
    price_top = bottom - foot_h - PRICE_H

    pdf.set_font('Roboto', '', 5)
    printed_on = tag.get('printed_on') or ''
    date_w = pdf.get_string_width(printed_on) + 0.6
    _write(pdf, right - date_w, oy + PAD_T, date_w, _pt(5) * 1.1, printed_on, align='R')

    pdf.set_font('Roboto', '', 10)
    name_w = inner_w - date_w - 0.8
    name_h = _pt(10) * 1.05
    name_lines = _lines(pdf, tag.get('name') or '', name_w, 2)
    for index, line in enumerate(name_lines):
        _write(pdf, left, oy + PAD_T + index * name_h, name_w, name_h, line)
    cursor = oy + PAD_T + max(len(name_lines), 1) * name_h + 0.4

    old_w = 0.0
    if tag.get('promo'):
        old_w = _draw_old_price(pdf, right, cursor, tag) + 1.0
    desc_w = inner_w - old_w
    pdf.set_font('Roboto', '', 7)
    desc_h = _pt(7) * 1.15
    max_desc = min(4, int((price_top - cursor - 0.3) / desc_h))
    for index, line in enumerate(_lines(pdf, tag.get('description') or '', desc_w, max_desc)):
        _write(pdf, left, cursor + index * desc_h, desc_w, desc_h, line)

    if tag.get('promo'):
        _draw_badge(pdf, ox + 0.2, price_top + (PRICE_H - BADGE_H) / 2)
    price_left = ox + 0.2 + BADGE_W + 0.6 if tag.get('promo') else left
    _draw_price(pdf, price_left, right, price_top + 0.2, tag)

    meta_w = 22.0
    meta_x = right - meta_w
    meta_lines = [('Цена за: ' + (tag.get('unit') or 'шт'), 'B', 6.6)]
    if tag.get('country'):
        meta_lines.append((tag['country'], '', 5.2))
    if tag.get('company'):
        meta_lines.append((tag['company'], '', 5.2))
    meta_heights = []
    for _text, style, size in meta_lines:
        meta_heights.append(_pt(size) * (1.05 if style == 'B' else 1.12))
    meta_y = bottom - sum(meta_heights)
    for (text, style, size), height in zip(meta_lines, meta_heights):
        pdf.set_font('Roboto', style, size)
        _write(pdf, meta_x, meta_y, meta_w, height, text, align='R')
        meta_y += height

    sku_h = _pt(5.4) * 1.15
    sku_y = bottom - foot_h
    pdf.set_font('Roboto', '', 5.4)
    sku = 'Код: ' + (tag.get('sku') or '')
    _write(pdf, left, sku_y, meta_x - left - 0.6, sku_h, sku)
    if bits:
        _draw_barcode(pdf, left, sku_y + sku_h + 0.25, bits)


def build_price_tags_pdf(tags: list[dict]) -> bytes:
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    _prepare(pdf)
    pdf.set_title('Ценники')
    if not tags:
        pdf.add_page()
        pdf.set_font('Roboto', '', 14)
        _write(pdf, 15, 20, 180, 8, 'Товары не выбраны.')
        return bytes(pdf.output())
    per_page = COLS * ROWS
    for index, tag in enumerate(tags):
        slot = index % per_page
        if slot == 0:
            pdf.add_page()
        col = slot % COLS
        row = slot // COLS
        _draw_tag(
            pdf,
            PAGE_X + col * (TAG_W + GAP),
            PAGE_Y + row * (TAG_H + GAP),
            tag,
        )
    return bytes(pdf.output())


def render_price_tags_pdf(tags: list[dict]) -> HttpResponse:
    try:
        payload = build_price_tags_pdf(tags)
    except ModuleNotFoundError:
        return HttpResponse(
            'Не удалось собрать PDF: на сервере не установлена библиотека fpdf2. '
            'В каталоге проекта выполните pip install -r requirements.txt и перезапустите сайт.',
            content_type='text/plain; charset=utf-8',
        )
    except Exception as exc:
        return HttpResponse(
            f'Не удалось собрать PDF: {exc}',
            content_type='text/plain; charset=utf-8',
        )
    response = HttpResponse(payload, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="cenniki.pdf"'
    return response
