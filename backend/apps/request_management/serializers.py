from rest_framework import serializers

from apps.users.models import User

from .models import Request


class RequestSerializer(serializers.ModelSerializer):
    admin_name = serializers.SerializerMethodField()
    assistant_name = serializers.SerializerMethodField()
    request_type_label = serializers.CharField(source='get_request_type_display', read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = Request
        fields = [
            'id', 'admin', 'admin_name', 'assistant', 'assistant_name',
            'created_at', 'request_type', 'request_type_label', 'message',
            'is_attended', 'attended_at', 'status',
        ]
        read_only_fields = [
            'id', 'admin_name', 'assistant', 'assistant_name', 'created_at',
            'request_type_label', 'is_attended', 'attended_at', 'status',
        ]

    def get_admin_name(self, obj):
        return obj.admin.full_name or obj.admin.username

    def get_assistant_name(self, obj):
        return obj.assistant.full_name or obj.assistant.username

    def get_status(self, obj):
        return 'atendido' if obj.is_attended else 'pendiente'

    def validate_admin(self, value):
        if not value.is_admin or not value.is_active:
            raise serializers.ValidationError('Selecciona un administrador activo.')
        return value

    def validate_message(self, value):
        if not value.strip():
            raise serializers.ValidationError('El mensaje es obligatorio.')
        return value.strip()

    def create(self, validated_data):
        request_user = self.context['request'].user
        return Request.objects.create(assistant=request_user, **validated_data)


class AdminOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'full_name', 'username']
