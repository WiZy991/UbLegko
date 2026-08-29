from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_sitevisit_visitor_key'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitevisit',
            name='device',
            field=models.CharField(blank=True, max_length=120, verbose_name='Устройство'),
        ),
        migrations.AddField(
            model_name='sitevisit',
            name='ip_address',
            field=models.GenericIPAddressField(blank=True, null=True, verbose_name='IP'),
        ),
    ]
