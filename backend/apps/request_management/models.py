from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Request(models.Model):
    SCHEDULE = 'horario'
    REPORT = 'reporte'
    REQUEST_TYPES = (
        (SCHEDULE, 'Cambio de horario'),
        (REPORT, 'Cambio en reporte'),
    )

    admin = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='assigned_requests',
        verbose_name='Administrador que revisa',
    )
    assistant = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='sent_requests',
        verbose_name='Asistente que envía',
    )
    report = models.ForeignKey(
        'time_logs.TimeLog',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='change_requests',
        verbose_name='Reporte relacionado',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES, verbose_name='Tipo de request')
    message = models.TextField(verbose_name='Mensaje del request')
    is_attended = models.BooleanField(default=False, verbose_name='Atendido')
    attended_at = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de atención')

    class Meta:
        db_table = 'requests'
        ordering = ['is_attended', '-created_at']
        verbose_name = 'Solicitud'
        verbose_name_plural = 'Solicitudes'

    def clean(self):
        if self.admin_id and (not self.admin.is_admin or not self.admin.is_active):
            raise ValidationError({'admin': 'El administrador seleccionado no está activo.'})
        if self.assistant_id and (
            not self.assistant.is_active
            or not self.assistant.role
            or self.assistant.role.code != 'asistente'
        ):
            raise ValidationError({'assistant': 'El usuario seleccionado debe ser un asistente activo.'})
        if self.request_type == self.REPORT and self.report_id is None:
            raise ValidationError({'report': 'Debes seleccionar el reporte que requiere el cambio.'})
        if self.request_type == self.SCHEDULE and self.report_id is not None:
            raise ValidationError({'report': 'Las solicitudes de horario no pueden tener un reporte relacionado.'})
        if self.report_id and self.assistant_id and self.report.assistant.user_id != self.assistant_id:
            raise ValidationError({'report': 'El reporte debe pertenecer al asistente que envía la solicitud.'})

    def mark_attended(self):
        self.is_attended = True
        self.attended_at = timezone.now()
        self.save(update_fields=['is_attended', 'attended_at'])

    def __str__(self):
        return f'{self.get_request_type_display()} - {self.assistant}'
