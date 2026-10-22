from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('request_management', '0001_initial'),
        ('time_logs', '0003_timelog_closed_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='request',
            name='report',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='change_requests',
                to='time_logs.timelog',
                verbose_name='Reporte relacionado',
            ),
        ),
    ]
