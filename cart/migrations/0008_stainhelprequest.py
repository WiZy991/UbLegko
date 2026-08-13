from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cart', '0007_order_site_feedback'),
        ('core', '0005_stain_help_request'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='StainHelpRequest',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('full_name', models.CharField(max_length=200, verbose_name='Имя')),
                        ('phone', models.CharField(max_length=40, verbose_name='Телефон')),
                        ('contact_method', models.CharField(max_length=300, verbose_name='Способ связи')),
                        ('problem', models.TextField(verbose_name='Что не отмывается')),
                        ('email_sent', models.BooleanField(default=False, verbose_name='Письмо отправлено')),
                        ('is_processed', models.BooleanField(default=False, verbose_name='Обработано')),
                        ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                        ('user', models.ForeignKey(
                            blank=True,
                            null=True,
                            on_delete=django.db.models.deletion.SET_NULL,
                            related_name='stain_help_requests',
                            to=settings.AUTH_USER_MODEL,
                            verbose_name='Пользователь',
                        )),
                    ],
                    options={
                        'verbose_name': 'Запрос',
                        'verbose_name_plural': 'Запросы',
                        'db_table': 'core_stainhelprequest',
                        'ordering': ['-created_at'],
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
