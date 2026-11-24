import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_sitepresence'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='ticker_speed_seconds',
            field=models.PositiveSmallIntegerField(
                default=18,
                help_text='Длительность одного круга в секундах. Чем меньше число, тем быстрее.',
                validators=[
                    django.core.validators.MinValueValidator(4),
                    django.core.validators.MaxValueValidator(180),
                ],
                verbose_name='Скорость, секунд',
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='ticker_text',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Если поле пустое, строка на сайте не показывается.',
                verbose_name='Текст',
            ),
        ),
    ]
