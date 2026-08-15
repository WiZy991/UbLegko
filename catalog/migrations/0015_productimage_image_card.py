# Generated manually for ProductImage.image_card

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0014_product_image_card'),
    ]

    operations = [
        migrations.AddField(
            model_name='productimage',
            name='image_card',
            field=models.ImageField(
                blank=True,
                editable=False,
                help_text='Автоматически создаётся для быстрой первой отрисовки галереи',
                upload_to='products/gallery/cards/',
                verbose_name='Превью для страницы товара',
            ),
        ),
    ]
