import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_sitesettings_ticker'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sitesettings',
            name='ticker_speed_seconds',
            field=models.PositiveSmallIntegerField(
                default=18,
                help_text=(
                    'Сколько секунд весь написанный текст едет один круг. '
                    '180 — три минуты, 600 — десять минут. Чем больше число, тем медленнее.'
                ),
                validators=[
                    django.core.validators.MinValueValidator(4),
                    django.core.validators.MaxValueValidator(600),
                ],
                verbose_name='Скорость, секунд',
            ),
        ),
    ]
