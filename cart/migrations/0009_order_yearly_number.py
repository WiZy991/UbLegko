from django.db import migrations, models
from django.utils import timezone


def backfill_order_numbers(apps, schema_editor):
    Order = apps.get_model('cart', 'Order')
    OrderYearCounter = apps.get_model('cart', 'OrderYearCounter')

    year_max = {}
    for order in Order.objects.order_by('created_at', 'pk'):
        year = timezone.localtime(order.created_at).year
        Order.objects.filter(pk=order.pk).update(
            number=order.pk,
            number_year=year,
        )
        year_max[year] = max(year_max.get(year, 0), order.pk)

    for year, last_number in year_max.items():
        OrderYearCounter.objects.create(year=year, last_number=last_number)


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0008_stainhelprequest'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderYearCounter',
            fields=[
                (
                    'year',
                    models.PositiveSmallIntegerField(
                        primary_key=True,
                        serialize=False,
                        verbose_name='Год',
                    ),
                ),
                (
                    'last_number',
                    models.PositiveIntegerField(default=0, verbose_name='Последний №'),
                ),
            ],
            options={
                'verbose_name': 'Счётчик заявок',
                'verbose_name_plural': 'Счётчики заявок',
            },
        ),
        migrations.AddField(
            model_name='order',
            name='number',
            field=models.PositiveIntegerField(editable=False, null=True, verbose_name='№'),
        ),
        migrations.AddField(
            model_name='order',
            name='number_year',
            field=models.PositiveSmallIntegerField(editable=False, null=True, verbose_name='Год №'),
        ),
        migrations.RunPython(backfill_order_numbers, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='order',
            name='number',
            field=models.PositiveIntegerField(editable=False, verbose_name='№'),
        ),
        migrations.AlterField(
            model_name='order',
            name='number_year',
            field=models.PositiveSmallIntegerField(editable=False, verbose_name='Год №'),
        ),
        migrations.AddConstraint(
            model_name='order',
            constraint=models.UniqueConstraint(
                fields=('number_year', 'number'),
                name='cart_order_unique_number_per_year',
            ),
        ),
    ]
