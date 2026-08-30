import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_sitevisit_geo'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitevisit',
            name='hit_count',
            field=models.PositiveIntegerField(default=1, verbose_name='Хитов за 5 мин'),
        ),
        migrations.AddField(
            model_name='sitevisit',
            name='last_hit_at',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Последний хит'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='sitevisit',
            name='ip_address',
            field=models.GenericIPAddressField(blank=True, db_index=True, null=True, verbose_name='IP'),
        ),
        migrations.AlterField(
            model_name='sitevisit',
            name='last_hit_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Последний хит'),
        ),
        migrations.CreateModel(
            name='BlockedIP',
            fields=[
                (
                    'ip_address',
                    models.GenericIPAddressField(
                        primary_key=True,
                        serialize=False,
                        verbose_name='IP',
                    ),
                ),
                ('blocked_until', models.DateTimeField(db_index=True, verbose_name='Заблокирован до')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Когда')),
            ],
            options={
                'verbose_name': 'Заблокированный IP',
                'verbose_name_plural': 'Заблокированные IP',
            },
        ),
        migrations.CreateModel(
            name='IPRateHit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip_address', models.GenericIPAddressField(db_index=True, verbose_name='IP')),
                ('hit_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Когда')),
            ],
            options={
                'verbose_name': 'Хит IP',
                'verbose_name_plural': 'Хиты IP',
            },
        ),
        migrations.AddIndex(
            model_name='sitevisit',
            index=models.Index(fields=['ip_address', 'visited_at'], name='core_sitevi_ip_addr_idx'),
        ),
        migrations.AddIndex(
            model_name='ipratehit',
            index=models.Index(fields=['ip_address', 'hit_at'], name='core_iprate_ip_hit_idx'),
        ),
    ]
