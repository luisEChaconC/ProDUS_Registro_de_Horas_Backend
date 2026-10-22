from rest_framework import serializers

from apps.users.models import User
from apps.time_logs.models import TimeLog

from .models import Request


class RequestSerializer(serializers.ModelSerializer):
    admin_name = serializers.SerializerMethodField()
    assistant_name = serializers.SerializerMethodField()
    request_type_label = serializers.CharField(source='get_request_type_display', read_only=True)
    status = serializers.SerializerMethodField()
    report_summary = serializers.SerializerMethodField()

    class Meta:
        model = Request
        fields = [
            'id', 'admin', 'admin_name', 'assistant', 'assistant_name',
            'created_at', 'request_type', 'request_type_label', 'message',
            'report', 'is_attended', 'attended_at', 'status', 'report_summary',
        ]
        read_only_fields = [
            'id', 'admin_name', 'assistant', 'assistant_name', 'created_at',
            'request_type_label', 'is_attended', 'attended_at', 'status', 'report_summary',
        ]

    def get_admin_name(self, obj):
        return obj.admin.full_name or obj.admin.username

    def get_assistant_name(self, obj):
        return obj.assistant.full_name or obj.assistant.username

    def get_status(self, obj):
        return 'atendido' if obj.is_attended else 'pendiente'

    def get_report_summary(self, obj):
        if not obj.report_id:
            return None
        report = obj.report
        return {
            'id': report.id,
            'check_in': report.check_in,
            'check_out': report.check_out,
            'project_name': report.project.name if report.project_id else None,
            'activities': report.activities,
            'work_description': report.work_description,
        }

    def validate_admin(self, value):
        if not value.is_admin or not value.is_active:
            raise serializers.ValidationError('Selecciona un administrador activo.')
        return value

    def validate_message(self, value):
        if not value.strip():
            raise serializers.ValidationError('El mensaje es obligatorio.')
        return value.strip()

    def validate(self, attrs):
        request_type = attrs.get('request_type')
        report = attrs.get('report')
        current_user = self.context['request'].user
        if request_type == Request.REPORT:
            if report is None:
                raise serializers.ValidationError({'report': 'Debes seleccionar un reporte.'})
            if report.assistant.user_id != current_user.id:
                raise serializers.ValidationError({'report': 'Solo puedes seleccionar tus propios reportes.'})
        elif report is not None:
            raise serializers.ValidationError({'report': 'Una solicitud de horario no puede incluir un reporte.'})
        return attrs

    def validate_report(self, value):
        if not isinstance(value, TimeLog):
            raise serializers.ValidationError('El reporte seleccionado no es válido.')
        return value

    def create(self, validated_data):
        request_user = self.context['request'].user
        return Request.objects.create(assistant=request_user, **validated_data)


class AdminOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'full_name', 'username']
