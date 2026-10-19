from django.db import migrations, models
import django.utils.timezone


def set_reactivation_dates_from_start_date(apps, schema_editor):
    Assistant = apps.get_model('users', 'Assistant')

    Assistant.objects.update(
        last_reactivation_date=models.F('start_date'),
    )


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0007_assistant_last_reactivation_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assistant',
            name='last_reactivation_date',
            field=models.DateField(
                default=django.utils.timezone.localdate,
                verbose_name='Fecha de última reactivación',
            ),
        ),
        migrations.RunPython(
            set_reactivation_dates_from_start_date,
            migrations.RunPython.noop,
        ),
    ]
