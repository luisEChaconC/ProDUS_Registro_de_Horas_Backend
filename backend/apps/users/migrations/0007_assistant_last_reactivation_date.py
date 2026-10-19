from django.db import migrations, models
import django.utils.timezone


def set_existing_reactivation_dates(apps, schema_editor):
    Assistant = apps.get_model('users', 'Assistant')

    for assistant in Assistant.objects.select_related('user').iterator():
        assistant.last_reactivation_date = assistant.user.created_at
        assistant.save(update_fields=['last_reactivation_date'])


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0006_normalize_roles'),
    ]

    operations = [
        migrations.AddField(
            model_name='assistant',
            name='last_reactivation_date',
            field=models.DateTimeField(
                default=django.utils.timezone.now,
                verbose_name='Fecha de última reactivación',
            ),
        ),
        migrations.RunPython(
            set_existing_reactivation_dates,
            migrations.RunPython.noop,
        ),
    ]
