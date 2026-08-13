from django.db import migrations
from django.db.models import Q


def sync_promo_from_old_price(apps, schema_editor):
    Product = apps.get_model('catalog', 'Product')
    Product.objects.filter(Q(old_price__isnull=True) | Q(old_price__lte=0)).update(
        is_promo=False
    )
    Product.objects.filter(old_price__isnull=False, old_price__gt=0).update(is_promo=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0012_product_recommendation_group'),
    ]

    operations = [
        migrations.RunPython(sync_promo_from_old_price, noop_reverse),
    ]
