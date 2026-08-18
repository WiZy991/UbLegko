from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_productpageview'),
    ]

    operations = [
        migrations.CreateModel(
            name='SearchQueryLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query', models.CharField(max_length=200, verbose_name='Запрос')),
                ('query_norm', models.CharField(db_index=True, max_length=200, verbose_name='Запрос (нормализованный)')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Когда')),
            ],
            options={
                'verbose_name': 'Статистика по поиску',
                'verbose_name_plural': 'Статистика по поиску',
                'indexes': [
                    models.Index(fields=['query_norm', 'created_at'], name='core_search_query_n_8a1c2d_idx'),
                ],
            },
        ),
    ]
