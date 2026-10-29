import hashlib
import ipaddress
import logging
import secrets
import smtplib
import socket
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.sessions.models import Session
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import (
    PasswordResetAuthorization,
    PasswordResetCode,
    PasswordResetIPThrottle,
    PasswordResetState,
)
from .validators import get_client_ip

logger = logging.getLogger(__name__)

CODE_EXPIRY = timedelta(minutes=10)
RESEND_INTERVAL = timedelta(seconds=60)
SEND_WINDOW = timedelta(minutes=30)
MAX_SENDS = 3
MAX_ATTEMPTS = 3
BLOCK_INTERVAL = timedelta(minutes=15)
AUTHORIZATION_EXPIRY = timedelta(minutes=10)


def invalidate_user_recovery(user):
    now = timezone.now()
    PasswordResetCode.objects.filter(user=user, used_at__isnull=True).update(
        invalidated_at=now
    )
    PasswordResetAuthorization.objects.filter(user=user, used_at__isnull=True).update(
        used_at=now
    )
    PasswordResetState.objects.filter(user=user).update(
        failed_attempts=0,
        blocked_until=None,
    )


def generate_recovery_code():
    return f'{secrets.randbelow(1_000_000):06d}'


def _client_ip(request):
    raw_ip = get_client_ip(request)
    if raw_ip:
        raw_ip = raw_ip.strip()
        try:
            ipaddress.ip_address(raw_ip)
            return raw_ip[:45]
        except ValueError:
            pass
    return '127.0.0.1'


def _generic_response_data(retry_after=60):
    return {
        'ok': True,
        'detail': 'Si la cuenta existe y tiene un correo institucional, recibirás un código.',
        'retry_after': retry_after,
    }


def request_password_reset(username, request):
    now = timezone.now()
    ip_address = _client_ip(request)
    reset_code = None
    user_email = None
    code = None

    with transaction.atomic():
        ip_state, _ = PasswordResetIPThrottle.objects.select_for_update().get_or_create(
            ip_address=ip_address,
            defaults={'window_started_at': now},
        )
        if now - ip_state.window_started_at >= SEND_WINDOW:
            ip_state.window_started_at = now
            ip_state.send_count = 0
        if ip_state.send_count >= 10:
            ip_state.save(update_fields=['window_started_at', 'send_count'])
            return _generic_response_data()
        ip_state.send_count += 1
        ip_state.save(update_fields=['window_started_at', 'send_count'])

        user = get_user_model().objects.filter(username=username.strip(), is_active=True).first()
        if user is None or not user.email:
            return _generic_response_data()

        user_state, _ = PasswordResetState.objects.select_for_update().get_or_create(
            user=user,
            defaults={'window_started_at': now},
        )
        if user_state.blocked_until and user_state.blocked_until > now:
            return _generic_response_data()

        if user_state.blocked_until and user_state.blocked_until <= now:
            user_state.blocked_until = None
            user_state.failed_attempts = 0

        if user_state.last_sent_at and now - user_state.last_sent_at < RESEND_INTERVAL:
            remaining = int((RESEND_INTERVAL - (now - user_state.last_sent_at)).total_seconds())
            return _generic_response_data(retry_after=max(1, remaining))

        if now - user_state.window_started_at >= SEND_WINDOW:
            user_state.window_started_at = now
            user_state.user_send_count = 0

        if user_state.user_send_count >= MAX_SENDS:
            user_state.save(update_fields=['window_started_at', 'user_send_count', 'blocked_until', 'failed_attempts'])
            return _generic_response_data()

        PasswordResetCode.objects.filter(user=user, used_at__isnull=True).update(
            invalidated_at=now
        )
        code = generate_recovery_code()
        reset_code = PasswordResetCode.objects.create(
            user=user,
            code_hash=make_password(code),
            expires_at=now + CODE_EXPIRY,
        )
        user_state.last_sent_at = now
        user_state.user_send_count += 1
        user_state.save(update_fields=['last_sent_at', 'user_send_count', 'window_started_at', 'blocked_until', 'failed_attempts'])
        user_email = user.email

    try:
        send_mail(
            'Restablecimiento de contraseña - Sistema de Registro de horas ProDUS',
            (
                'Hola,\n\n'
                'Hemos recibido una solicitud para restablecer la contraseña de tu cuenta.\n\n'
                f'Tu código de verificación es:\n\n{code}\n\n'
                'Este código expirará en 10 minutos.\n\n'
                'Si no solicitaste este cambio, puedes ignorar este correo.\n\n'
                'ProDUS - Universidad de Costa Rica'
            ),
            None,
            [user_email],
            fail_silently=False,
        )
    except (OSError, smtplib.SMTPException, socket.timeout, Exception) as exc:
        logger.warning('No se pudo enviar un correo de recuperación: %s', exc)
        if reset_code:
            PasswordResetCode.objects.filter(id=reset_code.id, used_at__isnull=True).update(invalidated_at=timezone.now())

    return _generic_response_data()


@transaction.atomic
def verify_password_reset(username, code):
    now = timezone.now()
    user = get_user_model().objects.filter(username=username.strip(), is_active=True).first()
    if user is None:
        return None

    user_state, _ = PasswordResetState.objects.select_for_update().get_or_create(
        user=user,
        defaults={'window_started_at': now},
    )
    if user_state.blocked_until and user_state.blocked_until > now:
        return None

    if user_state.blocked_until and user_state.blocked_until <= now:
        user_state.blocked_until = None
        user_state.failed_attempts = 0
        user_state.save(update_fields=['blocked_until', 'failed_attempts'])

    reset_code = (
        PasswordResetCode.objects.select_for_update()
        .filter(user=user, used_at__isnull=True, invalidated_at__isnull=True)
        .order_by('-created_at')
        .first()
    )
    if reset_code is None or reset_code.expires_at <= now:
        if reset_code:
            reset_code.invalidated_at = now
            reset_code.save(update_fields=['invalidated_at'])
        return None

    if not check_password(code, reset_code.code_hash):
        user_state.failed_attempts += 1
        if user_state.failed_attempts >= MAX_ATTEMPTS:
            user_state.blocked_until = now + BLOCK_INTERVAL
            reset_code.invalidated_at = now
            reset_code.save(update_fields=['invalidated_at'])
        user_state.save(update_fields=['failed_attempts', 'blocked_until'])
        return None

    reset_code.used_at = now
    reset_code.save(update_fields=['used_at'])

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
    PasswordResetAuthorization.objects.create(
        user=user,
        token_hash=token_hash,
        expires_at=now + AUTHORIZATION_EXPIRY,
    )
    user_state.failed_attempts = 0
    user_state.save(update_fields=['failed_attempts'])
    return token


@transaction.atomic
def reset_password(token, new_password):
    now = timezone.now()
    token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
    authorization = (
        PasswordResetAuthorization.objects.select_for_update()
        .filter(token_hash=token_hash, used_at__isnull=True, expires_at__gt=now)
        .first()
    )
    if authorization is None:
        authorizations = PasswordResetAuthorization.objects.select_for_update().filter(
            used_at__isnull=True,
            expires_at__gt=now,
        )
        authorization = next(
            (item for item in authorizations if check_password(token, item.token_hash)),
            None,
        )
    if authorization is None:
        return False

    user = get_user_model().objects.select_for_update().get(pk=authorization.user_id)
    user.set_password(new_password)
    user.needs_password_change = False
    user.save(update_fields=['password', 'updated_at', 'needs_password_change'])

    try:
        for session in Session.objects.filter(expire_date__gte=now):
            if session.get_decoded().get('_auth_user_id') == str(user.pk):
                session.delete()
    except Exception as exc:
        logger.warning('Error al invalidar sesiones de usuario: %s', exc)

    PasswordResetCode.objects.filter(user=user, used_at__isnull=True).update(invalidated_at=now)
    PasswordResetAuthorization.objects.filter(user=user, used_at__isnull=True).update(used_at=now)
    authorization.used_at = now
    authorization.save(update_fields=['used_at'])
    return True
