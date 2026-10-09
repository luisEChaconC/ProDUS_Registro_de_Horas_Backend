from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import AllowedIPRange, Assistant, Role, User


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'full_name', 'role')


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = '__all__'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = ['id', 'username', 'full_name', 'role', 'is_admin', 'is_active', 'created_at']
    list_editable = ['is_active']
    list_filter = ['role', 'is_admin', 'is_active']
    search_fields = ['username', 'full_name']
    ordering = ['username']
    raw_id_fields = ['role']
    actions = ['mark_as_active', 'mark_as_inactive']

    fieldsets = (
        (None, {'fields': ('username', 'full_name', 'role', 'password')}),
        ('Permisos', {'fields': ('is_admin', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'full_name', 'role', 'password1', 'password2', 'is_admin', 'is_active'),
        }),
    )

    @admin.action(description='Marcar usuarios seleccionados como activos')
    def mark_as_active(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description='Marcar usuarios seleccionados como inactivos')
    def mark_as_inactive(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'code']
    search_fields = ['id', 'code']
    ordering = ['code']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AllowedIPRange)
class AllowedIPRangeAdmin(admin.ModelAdmin):
    list_display = ['network', 'description', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['network', 'description']
    ordering = ['-is_active', 'network']


@admin.register(Assistant)
class AssistantAdmin(admin.ModelAdmin):
    list_display = ['user', 'start_date', 'end_date', 'weekly_hours']
    search_fields = ['user__username', 'user__full_name']
    list_filter = ['start_date', 'end_date']
