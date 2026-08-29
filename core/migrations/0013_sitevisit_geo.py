from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_sitevisit_ip_device'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitevisit',
            name='geo_city',
            field=models.CharField(blank=True, max_length=120, verbose_name='Город'),
        ),
        migrations.AddField(
            model_name='sitevisit',
            name='geo_country',
            field=models.CharField(blank=True, max_length=80, verbose_name='Страна'),
        ),
        migrations.AddField(
            model_name='sitevisit',
            name='geo_region',
            field=models.CharField(blank=True, max_length=120, verbose_name='Регион'),
        ),
    ]
