from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0010_slug_allow_unicode'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='short_description',
        ),
    ]
