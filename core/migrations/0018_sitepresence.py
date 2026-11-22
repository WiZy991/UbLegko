from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_blockedip_is_manual'),
    ]

    operations = [
        migrations.CreateModel(
            name='SitePresence',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'presence_key',
                    models.CharField(max_length=64, unique=True, verbose_name='Браузер'),
                ),
                (
                    'last_seen_at',
                    models.DateTimeField(db_index=True, verbose_name='Последний сигнал'),
                ),
            ],
            options={
                'verbose_name': 'Сейчас на сайте',
                'verbose_name_plural': 'Сейчас на сайте',
            },
        ),
    ]
