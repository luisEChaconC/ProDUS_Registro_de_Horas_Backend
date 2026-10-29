import hashlib
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory

from apps.users.models import (
    PasswordResetAuthorization,
    PasswordResetCode,
    PasswordResetState,
    Role,
    User,
)
from apps.users.recovery import CODE_EXPIRY, request_password_reset
from apps.users.serializers import AssistantCreateSerializer


class PasswordResetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_role, _ = Role.objects.get_or_create(code='admin')
        self.coordinator_role, _ = Role.objects.get_or_create(code='coordinador')
        self.assistant_role, _ = Role.objects.get_or_create(code='asistente')

        self.user = User.objects.create_user(
            username='usuario',
            password='Inicial123',
            email='usuario@ucr.ac.cr',
            role=self.assistant_role,
        )

        self.admin_user = User.objects.create_user(
            username='adminuser',
            password='Admin123Pass',
            email='admin@ucr.ac.cr',
            is_admin=True,
            role=self.admin_role,
        )

        self.coordinator_user = User.objects.create_user(
            username='coorduser',
            password='Coord123Pass',
            email='coord@ucr.ac.cr',
            is_admin=False,
            role=self.coordinator_role,
        )

    @patch('apps.users.recovery.generate_recovery_code', return_value='012345')
    def test_request_is_generic_and_code_is_hashed(self, _generate_code):
        response = self.client.post(
            '/api/users/auth/password-reset/request/',
            {'username': 'usuario'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('Si la cuenta existe', response.data['detail'])
        self.assertEqual(len(mail.outbox), 1)
        reset_code = PasswordResetCode.objects.get(user=self.user)
        self.assertNotEqual(reset_code.code_hash, '012345')
        self.assertIn('012345', mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, ['usuario@ucr.ac.cr'])

    def test_request_for_nonexistent_or_no_email_user_is_generic(self):
        # Non-existent user
        response = self.client.post(
            '/api/users/auth/password-reset/request/',
            {'username': 'no_existe'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('Si la cuenta existe', response.data['detail'])
        self.assertEqual(len(mail.outbox), 0)

        # User without email
        user_no_email = User.objects.create_user(
            username='sin_correo',
            password='Password123',
            email=None,
        )
        response2 = self.client.post(
            '/api/users/auth/password-reset/request/',
            {'username': user_no_email.username},
            format='json',
        )
        self.assertEqual(response2.status_code, 200)
        self.assertIn('Si la cuenta existe', response2.data['detail'])
        self.assertEqual(len(mail.outbox), 0)

    @patch('apps.users.recovery.generate_recovery_code', return_value='012345')
    def test_code_can_only_be_used_once(self, _generate_code):
        self.client.post(
            '/api/users/auth/password-reset/request/',
            {'username': 'usuario'},
            format='json',
        )
        response = self.client.post(
            '/api/users/auth/password-reset/verify/',
            {'username': 'usuario', 'code': '012345'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['ok'])
        self.assertIn('reset_token', response.data)

        second_response = self.client.post(
            '/api/users/auth/password-reset/verify/',
            {'username': 'usuario', 'code': '012345'},
            format='json',
        )
        self.assertEqual(second_response.status_code, 400)

    @patch('apps.users.recovery.generate_recovery_code', return_value='012345')
    def test_expired_code_is_rejected(self, _generate_code):
        self.client.post(
            '/api/users/auth/password-reset/request/',
            {'username': 'usuario'},
            format='json',
        )
        # Advance expires_at to the past
        reset_code = PasswordResetCode.objects.get(user=self.user)
        reset_code.expires_at = timezone.now() - timedelta(seconds=1)
        reset_code.save(update_fields=['expires_at'])

        response = self.client.post(
            '/api/users/auth/password-reset/verify/',
            {'username': 'usuario', 'code': '012345'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    @patch('apps.users.recovery.generate_recovery_code', return_value='012345')
    def test_resend_cooldown_60_seconds(self, _generate_code):
        # First request
        self.client.post(
            '/api/users/auth/password-reset/request/',
            {'username': 'usuario'},
            format='json',
        )
        self.assertEqual(len(mail.outbox), 1)

        # Immediate second request
        response = self.client.post(
            '/api/users/auth/password-reset/request/',
            {'username': 'usuario'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        # Still only 1 email sent because of 60s cooldown
        self.assertEqual(len(mail.outbox), 1)

    @patch('apps.users.recovery.generate_recovery_code', side_effect=['111111', '222222', '333333', '444444'])
    def test_max_3_sends_in_30_minutes(self, _generate_code):
        state, _ = PasswordResetState.objects.get_or_create(user=self.user)

        # 3 sends with simulated elapsed cooldown
        for _ in range(3):
            state.refresh_from_db()
            state.last_sent_at = timezone.now() - timedelta(seconds=65)
            state.save(update_fields=['last_sent_at'])
            self.client.post(
                '/api/users/auth/password-reset/request/',
                {'username': 'usuario'},
                format='json',
            )

        self.assertEqual(len(mail.outbox), 3)

        # 4th send attempt
        state.refresh_from_db()
        state.last_sent_at = timezone.now() - timedelta(seconds=65)
        state.save(update_fields=['last_sent_at'])

        response = self.client.post(
            '/api/users/auth/password-reset/request/',
            {'username': 'usuario'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        # Should still be 3 emails
        self.assertEqual(len(mail.outbox), 3)

    @patch('apps.users.recovery.generate_recovery_code', side_effect=['111111', '222222'])
    def test_new_code_invalidates_previous_code(self, _generate_code):
        self.client.post(
            '/api/users/auth/password-reset/request/',
            {'username': 'usuario'},
            format='json',
        )

        state = PasswordResetState.objects.get(user=self.user)
        state.last_sent_at = timezone.now() - timedelta(seconds=65)
        state.save(update_fields=['last_sent_at'])

        self.client.post(
            '/api/users/auth/password-reset/request/',
            {'username': 'usuario'},
            format='json',
        )

        # First code '111111' should fail
        res1 = self.client.post(
            '/api/users/auth/password-reset/verify/',
            {'username': 'usuario', 'code': '111111'},
            format='json',
        )
        self.assertEqual(res1.status_code, 400)

        # Second code '222222' should succeed
        res2 = self.client.post(
            '/api/users/auth/password-reset/verify/',
            {'username': 'usuario', 'code': '222222'},
            format='json',
        )
        self.assertEqual(res2.status_code, 200)

    @patch('apps.users.recovery.generate_recovery_code', return_value='012345')
    def test_3_failed_attempts_blocks_for_15_minutes(self, _generate_code):
        self.client.post(
            '/api/users/auth/password-reset/request/',
            {'username': 'usuario'},
            format='json',
        )

        # 3 wrong attempts
        for _ in range(3):
            res = self.client.post(
                '/api/users/auth/password-reset/verify/',
                {'username': 'usuario', 'code': '999999'},
                format='json',
            )
            self.assertEqual(res.status_code, 400)

        state = PasswordResetState.objects.get(user=self.user)
        self.assertIsNotNone(state.blocked_until)
        self.assertGreater(state.blocked_until, timezone.now())

        # Correct code is now also rejected because account is blocked
        res_correct = self.client.post(
            '/api/users/auth/password-reset/verify/',
            {'username': 'usuario', 'code': '012345'},
            format='json',
        )
        self.assertEqual(res_correct.status_code, 400)

    @patch('apps.users.recovery.generate_recovery_code', return_value='012345')
    def test_confirm_password_reset_success_and_cleanup(self, _generate_code):
        self.user.needs_password_change = True
        self.user.save()

        self.client.post(
            '/api/users/auth/password-reset/request/',
            {'username': 'usuario'},
            format='json',
        )
        verify_res = self.client.post(
            '/api/users/auth/password-reset/verify/',
            {'username': 'usuario', 'code': '012345'},
            format='json',
        )
        token = verify_res.data['reset_token']

        # Confirm password reset
        confirm_res = self.client.post(
            '/api/users/auth/password-reset/confirm/',
            {
                'reset_token': token,
                'new_password': 'NuevaContrasena1',
                'new_password_confirm': 'NuevaContrasena1',
            },
            format='json',
        )
        self.assertEqual(confirm_res.status_code, 200)

        # Check password was updated
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NuevaContrasena1'))
        self.assertFalse(self.user.needs_password_change)

        # Token cannot be reused
        reuse_res = self.client.post(
            '/api/users/auth/password-reset/confirm/',
            {
                'reset_token': token,
                'new_password': 'OtraContrasena2',
                'new_password_confirm': 'OtraContrasena2',
            },
            format='json',
        )
        self.assertEqual(reuse_res.status_code, 400)

    @patch('apps.users.recovery.generate_recovery_code', return_value='012345')
    def test_confirm_password_validation_rules(self, _generate_code):
        self.client.post(
            '/api/users/auth/password-reset/request/',
            {'username': 'usuario'},
            format='json',
        )
        verify_res = self.client.post(
            '/api/users/auth/password-reset/verify/',
            {'username': 'usuario', 'code': '012345'},
            format='json',
        )
        token = verify_res.data['reset_token']

        # Mismatch
        res_mismatch = self.client.post(
            '/api/users/auth/password-reset/confirm/',
            {
                'reset_token': token,
                'new_password': 'Password123',
                'new_password_confirm': 'Password456',
            },
            format='json',
        )
        self.assertEqual(res_mismatch.status_code, 400)

        # No uppercase
        res_no_upper = self.client.post(
            '/api/users/auth/password-reset/confirm/',
            {
                'reset_token': token,
                'new_password': 'password123',
                'new_password_confirm': 'password123',
            },
            format='json',
        )
        self.assertEqual(res_no_upper.status_code, 400)

        # No digit
        res_no_digit = self.client.post(
            '/api/users/auth/password-reset/confirm/',
            {
                'reset_token': token,
                'new_password': 'PasswordOnly',
                'new_password_confirm': 'PasswordOnly',
            },
            format='json',
        )
        self.assertEqual(res_no_digit.status_code, 400)

    @patch('apps.users.recovery.generate_recovery_code', return_value='012345')
    def test_email_change_invalidates_recovery(self, _generate_code):
        self.client.post(
            '/api/users/auth/password-reset/request/',
            {'username': 'usuario'},
            format='json',
        )

        # Admin changes the email
        self.user.email = 'nuevo_correo@ucr.ac.cr'
        self.user.save()

        # The previously issued code should now be invalid
        res = self.client.post(
            '/api/users/auth/password-reset/verify/',
            {'username': 'usuario', 'code': '012345'},
            format='json',
        )
        self.assertEqual(res.status_code, 400)

    def test_non_institutional_email_is_rejected(self):
        self.user.email = 'usuario@example.com'
        with self.assertRaises(ValidationError):
            self.user.save()

    def test_email_normalization_and_case_insensitivity(self):
        self.user.email = '  Usuario.Test@UCR.AC.CR  '
        self.user.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'usuario.test@ucr.ac.cr')

    def test_email_with_dots_is_valid(self):
        self.user.email = 'ana.torressolano@ucr.ac.cr'
        self.user.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'ana.torressolano@ucr.ac.cr')

    def test_coordinator_cannot_assign_email(self):
        factory = APIRequestFactory()
        request = factory.post('/api/users/assistants/')
        request.user = self.coordinator_user

        serializer = AssistantCreateSerializer(
            data={
                'username': 'nuevoasistente',
                'full_name': 'Nuevo Asistente',
                'email': 'asistente@ucr.ac.cr',
                'password': 'Password123',
                'password_confirm': 'Password123',
                'start_date': '2026-01-01',
                'weekly_hours': 10,
            },
            context={'request': request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_admin_can_assign_email(self):
        factory = APIRequestFactory()
        request = factory.post('/api/users/assistants/')
        request.user = self.admin_user

        serializer = AssistantCreateSerializer(
            data={
                'username': 'nuevoasistente2',
                'full_name': 'Nuevo Asistente 2',
                'email': 'asistente2@ucr.ac.cr',
                'password': 'Password123',
                'password_confirm': 'Password123',
                'start_date': '2026-01-01',
                'weekly_hours': 10,
            },
            context={'request': request},
        )
        self.assertTrue(serializer.is_valid())
