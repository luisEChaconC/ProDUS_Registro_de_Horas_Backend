from django.db import migrations, models
import django.utils.timezone
import apps.users.models


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0008_assistant_reactivation_date_from_start'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='email',
            field=models.EmailField(
                blank=True,
                max_length=254,
                null=True,
                validators=[apps.users.models.validate_institute_email],
                verbose_name='Correo institucional',
            ),
        ),
        migrations.CreateModel(
            name='PasswordResetAuthorization',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token_hash', models.CharField(max_length=128)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='password_reset_authorizations', to='users.user')),
            ],
        ),
        migrations.CreateModel(
            name='PasswordResetCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code_hash', models.CharField(max_length=128)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('invalidated_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='password_reset_codes', to='users.user')),
            ],
        ),
        migrations.CreateModel(
            name='PasswordResetIPThrottle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip_address', models.GenericIPAddressField(unique=True)),
                ('window_started_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('send_count', models.PositiveSmallIntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='PasswordResetState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_sent_at', models.DateTimeField(blank=True, null=True)),
                ('window_started_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('user_send_count', models.PositiveSmallIntegerField(default=0)),
                ('failed_attempts', models.PositiveSmallIntegerField(default=0)),
                ('blocked_until', models.DateTimeField(blank=True, null=True)),
                ('user', models.OneToOneField(on_delete=models.deletion.CASCADE, related_name='password_reset_state', to='users.user')),
            ],
        ),
        migrations.AddIndex(
            model_name='passwordresetauthorization',
            index=models.Index(fields=['user', 'used_at', 'expires_at'], name='users_passw_user_id_6e94d0_idx'),
        ),
        migrations.AddIndex(
            model_name='passwordresetcode',
            index=models.Index(fields=['user', 'created_at'], name='users_passw_user_id_0b1c8b_idx'),
        ),
        migrations.AddIndex(
            model_name='passwordresetcode',
            index=models.Index(fields=['user', 'used_at', 'invalidated_at'], name='users_passw_user_id_fad7c0_idx'),
        ),
    ]
