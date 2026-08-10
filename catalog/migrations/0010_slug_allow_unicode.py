from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0009_product_search_text'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='slug',
            field=models.SlugField(
                allow_unicode=True,
                blank=True,
                help_text='Адрес страницы в URL. Можно оставить пустым — создастся из названия.',
                max_length=220,
                unique=True,
                verbose_name='Слаг',
            ),
        ),
        migrations.AlterField(
            model_name='product',
            name='slug',
            field=models.SlugField(
                allow_unicode=True,
                blank=True,
                help_text='Адрес страницы в URL. Можно оставить пустым — создастся из названия.',
                max_length=280,
                unique=True,
                verbose_name='Слаг',
            ),
        ),
    ]
