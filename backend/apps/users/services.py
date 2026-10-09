from django.core.exceptions import ValidationError

from django.db import transaction
from .validators import get_client_ip, is_valid_institute_ip
from .models import User, Role, Assistant

class UserService:
    @staticmethod
    @transaction.atomic
    def create_user(
        *,
        full_name,
        username,
        role_code,
        password,
        is_active=True,
        is_admin=False,
        needs_password_change=False,
    ) -> User:
        user = User.objects.create_user(
            username=username,
            password=password,
            full_name=full_name,
            is_active=is_active,
            is_admin=is_admin,
            needs_password_change=needs_password_change,
        )

        role, _ = Role.objects.get_or_create(code=role_code)
        user.role = role
        user.save(update_fields=['role'])

        return user
    @staticmethod
    def username_exists(username) -> bool:
        return User.objects.filter(username=username).exists()

class AssistantService:
    @staticmethod
    @transaction.atomic
    def create_assistant_with_user(*, full_name, username, password, start_date, weekly_hours, is_active=True, end_date=None) -> Assistant:
        user = UserService().create_user(
            full_name=full_name,
            username=username,
            role_code='asistente',
            password=password,
            is_active=is_active,
            is_admin=False,
            needs_password_change=True,
        )

        assistant = AssistantService().create_assistant(
            user=user,
            start_date=start_date,
            end_date=end_date,
            weekly_hours=weekly_hours,
        )

        return assistant

    @staticmethod
    @transaction.atomic
    def create_assistant(*, user, start_date, weekly_hours, end_date=None) -> Assistant:
        assistant = Assistant.objects.create(
            user=user,
            start_date=start_date,
            end_date=end_date,
            weekly_hours=weekly_hours,
        )

        return assistant

def validate_institute_ip_addr(request):
    client_ip = get_client_ip(request)
    is_allowed = is_valid_institute_ip(request)

    return {
        'allowed': is_allowed,
        'client_ip': client_ip,
        'message': 'Acceso permitido' if is_allowed else 'Acceso denegado - IP no autorizada',
    }


def change_user_password(user, current_password, new_password, neet_force_change):
    if not user.check_password(current_password):
        raise ValidationError({'current_password': 'La contraseña actual es incorrecta.'})

    user.set_password(new_password)
    user.needs_password_change = neet_force_change
    user.save(update_fields=['password', 'needs_password_change'])
    return user
