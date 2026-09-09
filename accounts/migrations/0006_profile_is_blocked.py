from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_seed_default_groups'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='is_blocked',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text='Отдельный флаг блокировки (не путать с неподтверждённым email).',
                verbose_name='Заблокирован',
            ),
        ),
    ]
