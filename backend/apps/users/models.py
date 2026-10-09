from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


ROLE_CODES = ('asistente', 'coordinador', 'admin')


class Role(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name='Código')

    def save(self, *args, **kwargs):
        self.code = (self.code or '').strip().lower()
        super().save(*args, **kwargs)

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.code not in ROLE_CODES:
            raise ValidationError({
                'code': 'El rol debe ser asistente, coordinador o admin.'
            })

    class Meta:
        db_table = 'role'
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'
        ordering = ['code']

    def __str__(self):
        return self.code


class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('El usuario debe tener un nombre de usuario')

        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    full_name = models.CharField(max_length=150, default='', verbose_name='Nombre completo')
    username = models.CharField(max_length=255, unique=True, verbose_name='Nombre de usuario')
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='Rol',
    )
    is_admin = models.BooleanField(default=False, verbose_name='Es administrador')
    is_active = models.BooleanField(default=True, verbose_name='Está activo')
    is_staff = models.BooleanField(default=False, verbose_name='Es staff')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')
    # nuevo atributo para forzar cambio de contraseña
    needs_password_change = models.BooleanField(default=False, verbose_name='Necesita cambio de contraseña')

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'user'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def clean(self):
        from django.core.exceptions import ValidationError

        super().clean()
        if self.role_id and self.role and self.role.code not in ROLE_CODES:
            raise ValidationError({
                'role': 'El rol debe ser asistente, coordinador o admin.'
            })

    def __str__(self):
        return self.full_name or self.username


class Assistant(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='assistant',
        verbose_name='Usuario',
    )
    start_date = models.DateField(verbose_name='Fecha de inicio')
    end_date = models.DateField(null=True, blank=True, verbose_name='Fecha de finalización')
    weekly_hours = models.IntegerField(verbose_name='Horas semanales')

    class Meta:
        db_table = 'assistant'
        verbose_name = 'Asistente'
        verbose_name_plural = 'Asistentes'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(weekly_hours__gt=0),
                name='assistant_weekly_hours_gt_0',
            ),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.user_id and self.user.role and self.user.role.code != 'asistente':
            raise ValidationError({
                'user': 'El usuario seleccionado debe tener el rol asistente.'
            })

    def __str__(self):
        return self.user.full_name or self.user.username


class AllowedIPRange(models.Model):
    network = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Red o IP (CIDR)',
        help_text='Formato CIDR (ej: 192.168.1.0/24) o IP individual (ej: 192.168.1.1)',
    )
    description = models.CharField(max_length=200, blank=True, verbose_name='Descripción')
    is_active = models.BooleanField(default=True, verbose_name='Está activo')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')

    class Meta:
        db_table = 'allowed_ip_range'
        verbose_name = 'Rango IP Permitido'
        verbose_name_plural = 'Rangos IP Permitidos'
        ordering = ['-is_active', 'network']

    def __str__(self):
        return f"{self.network} - {self.description}" if self.description else self.network
