from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import AllowedIPRange, Role, User, Assistant
from .services import UserService, AssistantService
from apps.schedules.serializers import ScheduleBlockCreateSerializer


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'code']


class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='role.code', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'username', 'role', 'is_admin', 'is_active', 'needs_password_change', 'created_at']
        read_only_fields = ['id', 'created_at']


class AllowedIPRangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AllowedIPRange
        fields = ['id', 'network', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['full_name'] = user.full_name
        token['role'] = user.role.code if user.role else None
        token['is_admin'] = user.is_admin
        token['needs_password_change'] = user.needs_password_change
        return token

    def validate(self, attrs):
        username = attrs.get('username')
        if username:
            user = User.objects.filter(username=username).first()
            if user and not user.is_active:
                raise serializers.ValidationError({'detail': 'Usuario inactivo. Contacte al administrador.'})

        data = super().validate(attrs)
        data['ok'] = True 
        data['user'] = {
            'id': self.user.id,
            'full_name': self.user.full_name,
            'username': self.user.username,
            'is_active': self.user.is_active,
            'role': self.user.role.code if self.user.role else None,
            'is_admin': self.user.is_admin,
            'needs_password_change': self.user.needs_password_change,
        }
        return data
    
class AssistantCreateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    username = serializers.CharField(max_length=255)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    is_active = serializers.BooleanField(required=False, default=True)

    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False, allow_null=True)
    weekly_hours = serializers.IntegerField(min_value=1, max_value=168)
    schedule_blocks = ScheduleBlockCreateSerializer(many=True, required=False, default=list)

    def validate_username(self, value):
        if UserService.username_exists(username=value):
            raise serializers.ValidationError('Ya existe un usuario con ese username.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Las contraseñas no coinciden.'})

        end_date = attrs.get('end_date')
        if end_date and end_date < attrs['start_date']:
            raise serializers.ValidationError({'end_date': 'La fecha de finalización no puede ser anterior a la fecha de inicio.'})

        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        schedule_blocks = validated_data.pop('schedule_blocks', [])
        return AssistantService.create_assistant_with_user(
            schedule_blocks=schedule_blocks,
            **validated_data,
        )

class AssistantListSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)

    class Meta:
        model = Assistant
        fields = ['id', 'username', 'full_name', 'is_active']

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True, min_length=8)
    needs_password_change = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'Las contraseñas nuevas no coinciden.'
            })

        password = attrs['new_password']
        if not any(char.isupper() for char in password):
            raise serializers.ValidationError({
                'new_password': 'Debe tener al menos una mayúscula.'
            })
        if not any(char.isdigit() for char in password):
            raise serializers.ValidationError({
                'new_password': 'Debe tener al menos un número.'
            })

        return attrs
class AssistantDetailSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    is_active = serializers.CharField(source='user.is_active ', read_only=True)
    role = serializers.CharField(source='user.role', read_only=True)

    class Meta:
        model = Assistant
        fields = [
            'id',
            'username',
            'full_name',
            'is_active',
            'role',
            'start_date',
            'end_date',
            'weekly_hours',
        ]
