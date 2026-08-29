from django.db import migrations, models


def reset_inflated_site_visits(apps, schema_editor):
    """Старые записи считали каждую страницу — очищаем перед корректным учётом."""
    SiteVisit = apps.get_model('core', 'SiteVisit')
    SiteVisit.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_sitevisit'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitevisit',
            name='visitor_key',
            field=models.CharField(
                blank=True,
                db_index=True,
                default='',
                max_length=64,
                verbose_name='Посетитель',
            ),
        ),
        migrations.RunPython(reset_inflated_site_visits, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='sitevisit',
            name='visitor_key',
            field=models.CharField(db_index=True, max_length=64, verbose_name='Посетитель'),
        ),
        migrations.AddIndex(
            model_name='sitevisit',
            index=models.Index(
                fields=['visitor_key', 'visited_at'],
                name='core_sitevi_visitor_4f8a21_idx',
            ),
        ),
    ]
