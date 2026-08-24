from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_sitesettings_stain_help_auto_modal'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteVisit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('path', models.CharField(blank=True, max_length=300, verbose_name='Страница')),
                ('visited_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Когда')),
            ],
            options={
                'verbose_name': 'Заход на сайт',
                'verbose_name_plural': 'Заходы на сайт',
                'indexes': [models.Index(fields=['visited_at'], name='core_sitevi_visited_6a8b0d_idx')],
            },
        ),
    ]
