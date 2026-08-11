from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0006_order_email_sent'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='site_feedback',
            field=models.TextField(blank=True, verbose_name='Комментарий по сайту'),
        ),
    ]
