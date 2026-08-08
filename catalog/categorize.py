from catalog.models import Category

# Более специфичные правила выше — срабатывает первое совпадение.
CATEGORY_RULES = [
    (
        'Для машины',
        [
            'bahler', 'автомоб', 'автотранспорт', 'кузов', 'лкп', 'шин', 'резин',
            'двигател', 'дисков', 'фар', 'стекол', 'салона', 'бесконтактн',
            'чернитель', 'антидождь', 'насеком', 'воск', 'полирол', 'полировк',
        ],
    ),
    (
        'Химчистка',
        [
            'axel', 'пятновывод', 'химчист', 'ковр', 'enzitop', 'мягк. мебел',
            'мягкой мебел', 'мебели', 'ткан', 'крови', 'мочи',
        ],
    ),
    (
        'Для стирки',
        [
            'стирк', 'delin', 'dezet', 'отбеливатель для ткани', 'белья', 'одежды',
        ],
    ),
    (
        'Для посудомоечных машин',
        [
            'посудомоеч', 'dishwash', 'кофемаш', 'coffer', 'посуды через',
            'мойки посуды', 'dream', 'bel (',
        ],
    ),
    (
        'Мыло',
        [
            'мыло', 'cream soap', 'крем-мыло', 'увлажняющее крем',
        ],
    ),
    (
        'Антисептики',
        [
            'антисептик', 'dez', 'clf', 'дезинфек', 'изопропанол',
        ],
    ),
    (
        'Освежители и поглотители',
        [
            'ароматизатор', 'aroma', 'освежител', 'поглотител', 'запаха',
        ],
    ),
    (
        'Пищевое производство',
        [
            'пищев', 'пароконвектомат', 'санитарной мойки', 'astrix', 'citrus degreaser',
        ],
    ),
    (
        'Масла и смазки',
        [
            'смазк', 'масл', 'lubric',
        ],
    ),
    (
        'Деревообработка',
        [
            'дерев', 'wood',
        ],
    ),
    (
        'Услуги',
        [
            'услуг', 'service',
        ],
    ),
    (
        'Сопутствующие товары',
        [
            'дозатор', 'инвентар', 'тряпк', 'перчатк', 'ведро',
        ],
    ),
    (
        'Общая уборка',
        [
            'alfa', 'amol', 'asin', 'моющ', 'чистк', 'сантехник', 'ржавчин',
            'ремонт', 'концентрат', 'универсальн', 'обезжир', 'налета', 'налёта',
            'фасад', 'пол', 'стен',
        ],
    ),
]

FALLBACK_CATEGORY = 'Общая уборка'
IMPORT_CATEGORY_NAME = 'Импортированные товары'


def _normalize(text: str) -> str:
    return (text or '').lower().replace('ё', 'е')


def detect_category_name(product_name: str, description: str = '') -> str:
    haystack = f'{_normalize(product_name)} {_normalize(description)}'
    for category_name, keywords in CATEGORY_RULES:
        for keyword in keywords:
            if keyword and keyword in haystack:
                return category_name
    return FALLBACK_CATEGORY


def get_or_create_category(name: str) -> Category:
    category, _ = Category.objects.get_or_create(
        name=name,
        defaults={'is_visible': True},
    )
    if not category.is_visible:
        category.is_visible = True
        category.save(update_fields=['is_visible'])
    return category


def resolve_category(product_name: str, description: str = '', explicit_category: str = '') -> Category:
    if explicit_category and explicit_category.strip() != IMPORT_CATEGORY_NAME:
        return get_or_create_category(explicit_category.strip())
    detected = detect_category_name(product_name, description)
    return get_or_create_category(detected)


def reassign_imported_products() -> tuple[int, int]:
    """Переносит товары из «Импортированные товары» по авто-правилам."""
    import_cat = Category.objects.filter(name=IMPORT_CATEGORY_NAME).first()
    moved = 0
    if import_cat:
        for product in import_cat.products.all():
            product.category = resolve_category(product.name, product.description or '')
            product.save(update_fields=['category'])
            moved += 1
        if not import_cat.products.exists():
            import_cat.delete()

    # На всякий случай пересчитать товары без категории не нужно (FK обязателен)
    return moved, Category.objects.filter(name=IMPORT_CATEGORY_NAME).count()
