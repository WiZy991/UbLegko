import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_ticker_speed_range'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='ticker_font',
            field=models.CharField(
                choices=[
                    ('manrope', 'Manrope'),
                    ('arial', 'Arial'),
                    ('verdana', 'Verdana'),
                    ('tahoma', 'Tahoma'),
                    ('segoe', 'Segoe UI'),
                    ('trebuchet', 'Trebuchet MS'),
                    ('georgia', 'Georgia'),
                    ('times', 'Times New Roman'),
                    ('courier', 'Courier New'),
                    ('impact', 'Impact'),
                    ('oswald', 'Oswald'),
                    ('rubik', 'Rubik'),
                    ('montserrat', 'Montserrat'),
                    ('playfair', 'Playfair Display'),
                    ('comfortaa', 'Comfortaa'),
                    ('russo', 'Russo One'),
                    ('ptserif', 'PT Serif'),
                ],
                default='manrope',
                max_length=32,
                verbose_name='Шрифт',
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='ticker_font_size',
            field=models.PositiveSmallIntegerField(
                default=32,
                help_text='Размер на компьютере, в пикселях. На телефоне шрифт остаётся небольшим.',
                validators=[
                    django.core.validators.MinValueValidator(12),
                    django.core.validators.MaxValueValidator(72),
                ],
                verbose_name='Размер шрифта',
            ),
        ),
        migrations.AlterField(
            model_name='sitesettings',
            name='ticker_speed_seconds',
            field=models.PositiveSmallIntegerField(
                default=18,
                help_text=(
                    'Сколько секунд весь написанный текст едет один круг. '
                    'От 4 до 1000. Чем больше число, тем медленнее.'
                ),
                validators=[
                    django.core.validators.MinValueValidator(4),
                    django.core.validators.MaxValueValidator(1000),
                ],
                verbose_name='Скорость, секунд',
            ),
        ),
    ]
