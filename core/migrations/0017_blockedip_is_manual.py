from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_sitevisit_last_hit_index'),
    ]

    operations = [
        migrations.AddField(
            model_name='blockedip',
            name='is_manual',
            field=models.BooleanField(default=False, verbose_name='Вручную'),
        ),
    ]
