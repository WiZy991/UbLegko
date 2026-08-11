from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0005_city_note_and_order_city'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='email_sent',
            field=models.BooleanField(default=False, verbose_name='Письмо отправлено'),
        ),
    ]
