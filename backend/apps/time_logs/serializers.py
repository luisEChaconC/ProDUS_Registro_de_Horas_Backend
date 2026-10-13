from rest_framework import serializers
from django.utils import timezone

from apps.time_logs.models import TimeLog


class TimeLogSerializer(serializers.ModelSerializer):
    status_code = serializers.CharField(source='status.code', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True, allow_null=True)
    manager_name = serializers.SerializerMethodField()
    notes = serializers.CharField(source='decision_comment', read_only=True)
    elapsed_seconds = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = TimeLog
        fields = [
            'id',
            'check_in',
            'check_out',
            'status_code',
            'project_name',
            'manager_name',
            'work_description',
            'activities',
            'notes',
            'break_minutes',
            'elapsed_seconds',
            'is_active',
        ]
        read_only_fields = ['check_in', 'status_code']

    def get_elapsed_seconds(self, obj):
        end_moment = obj.check_out or timezone.now()
        return int((end_moment - obj.check_in).total_seconds())

    def get_is_active(self, obj):
        return obj.check_out is None and getattr(obj.status, 'code', None) == 'IN_PROGRESS'

    def get_manager_name(self, obj):
        if not obj.manager_user:
            return None
        return obj.manager_user.full_name or obj.manager_user.username


class AdminTimeLogSerializer(TimeLogSerializer):
    class Meta(TimeLogSerializer.Meta):
        read_only_fields = ['id', 'check_in', 'status_code', 'elapsed_seconds', 'is_active']


class WorkSessionCloseInputSerializer(serializers.Serializer):
    project_id = serializers.IntegerField(required=False, allow_null=True)
    manager_user_id = serializers.IntegerField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=500)
    activities = serializers.CharField(required=False, allow_blank=True)
    break_minutes = serializers.IntegerField(required=False, min_value=0, default=0)