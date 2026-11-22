from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0001_initial'),
        ('core', '0014_sitevisit_freeze_ddos'),
    ]

    operations = [
        migrations.CreateModel(
            name='IPBlacklist',
            fields=[],
            options={
                'verbose_name': 'Чёрный список',
                'verbose_name_plural': 'Чёрный список',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('core.blockedip',),
        ),
    ]
