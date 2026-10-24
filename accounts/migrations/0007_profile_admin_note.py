from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_profile_is_blocked'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='admin_note',
            field=models.CharField(
                blank=True,
                help_text='Только для админки. Клиент не видит. Показывается в скобках рядом с именем в заявках.',
                max_length=200,
                verbose_name='Кто это (заметка админа)',
            ),
        ),
    ]
