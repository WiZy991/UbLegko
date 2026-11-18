from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_sitesettings_ddos_limits'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sitevisit',
            name='last_hit_at',
            field=models.DateTimeField(
                auto_now_add=True,
                db_index=True,
                verbose_name='Последний хит',
            ),
        ),
    ]
