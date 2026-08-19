from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_searchquerylog'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='stain_help_auto_modal',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'Если включено, посетитель один раз за визит увидит форму '
                    '«Что-то не отмывается» сразу при входе на сайт. '
                    'Дальше окно открывается только по нажатию на слоган.'
                ),
                verbose_name='Активировать автоматически модальное окно',
            ),
        ),
    ]
