from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_ticker_font_and_speed_limit'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sitesettings',
            name='ticker_font',
            field=models.CharField(
                choices=[
                    ('manrope', 'Manrope'),
                    ('arial', 'Arial'),
                    ('arialblack', 'Arial Black'),
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
    ]
