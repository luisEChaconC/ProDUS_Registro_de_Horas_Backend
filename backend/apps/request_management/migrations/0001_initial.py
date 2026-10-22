from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Request',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')),
                ('request_type', models.CharField(choices=[('horario', 'Cambio de horario'), ('reporte', 'Cambio en reporte')], max_length=20, verbose_name='Tipo de request')),
                ('message', models.TextField(verbose_name='Mensaje del request')),
                ('is_attended', models.BooleanField(default=False, verbose_name='Atendido')),
                ('attended_at', models.DateTimeField(blank=True, null=True, verbose_name='Fecha de atención')),
                ('admin', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='assigned_requests', to=settings.AUTH_USER_MODEL, verbose_name='Administrador que revisa')),
                ('assistant', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sent_requests', to=settings.AUTH_USER_MODEL, verbose_name='Asistente que envía')),
            ],
            options={
                'verbose_name': 'Solicitud',
                'verbose_name_plural': 'Solicitudes',
                'db_table': 'requests',
                'ordering': ['is_attended', '-created_at'],
            },
        ),
    ]
