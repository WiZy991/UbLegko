from django.db import migrations, models


def populate_search_text(apps, schema_editor):
    Product = apps.get_model('catalog', 'Product')
    for product in Product.objects.iterator():
        parts = (
            product.name,
            product.short_description,
            product.description,
            product.sku,
            product.country,
        )
        product.search_text = ' '.join(
            p.strip() for p in parts if p and p.strip()
        ).casefold()
        product.save(update_fields=['search_text'])


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0008_sync_promo_from_old_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='search_text',
            field=models.TextField(blank=True, editable=False, verbose_name='Поисковый индекс'),
        ),
        migrations.RunPython(populate_search_text, migrations.RunPython.noop),
    ]
