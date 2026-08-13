from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_stain_help_request'),
        ('cart', '0008_stainhelprequest'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='StainHelpRequest'),
            ],
            database_operations=[],
        ),
    ]
