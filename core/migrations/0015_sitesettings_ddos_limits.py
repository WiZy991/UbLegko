from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_sitevisit_freeze_ddos'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='ddos_rate_limit_hits',
            field=models.PositiveIntegerField(
                default=15,
                help_text='Сколько запросов с одного IP за окно времени — и IP блокируется на 1 час.',
                verbose_name='DDoS: хитов',
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='ddos_rate_window_seconds',
            field=models.PositiveIntegerField(
                default=10,
                help_text='Окно времени в секундах для подсчёта хитов.',
                verbose_name='DDoS: секунд',
            ),
        ),
    ]
