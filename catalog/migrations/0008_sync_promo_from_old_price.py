from django.db import migrations
from django.db.models import F, Q


def sync_promo_from_old_price(apps, schema_editor):
    Product = apps.get_model('catalog', 'Product')
    Product.objects.filter(
        old_price__isnull=False,
        old_price__gt=0,
    ).filter(
        Q(is_promo=False) | Q(old_price__gt=F('price')) | Q(old_price__lte=F('price'))
    ).update(is_promo=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0007_productimage_verbose'),
    ]

    operations = [
        migrations.RunPython(sync_promo_from_old_price, noop_reverse),
    ]
