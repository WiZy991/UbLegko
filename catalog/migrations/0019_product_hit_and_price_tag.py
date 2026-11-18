from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0018_product_is_new'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='is_hit',
            field=models.BooleanField(default=False, verbose_name='Хит продаж'),
        ),
        migrations.AddField(
            model_name='product',
            name='price_tag_description',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Текст для печати ценника. На сайте посетителям не показывается.',
                verbose_name='Описание для ценника',
            ),
        ),
    ]
