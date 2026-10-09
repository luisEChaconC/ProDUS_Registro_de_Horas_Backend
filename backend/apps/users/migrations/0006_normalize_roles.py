from django.db import migrations


def normalize_roles(apps, schema_editor):
    Role = apps.get_model('users', 'Role')
    User = apps.get_model('users', 'User')

    assistant_role, _ = Role.objects.get_or_create(code='asistente')
    coordinator_role, _ = Role.objects.get_or_create(code='coordinador')
    Role.objects.get_or_create(code='admin')

    User.objects.filter(role__code='assistant').update(role=assistant_role)
    User.objects.filter(role__code='coordinator').update(role=coordinator_role)


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0005_user_needs_password_change'),
    ]

    operations = [
        migrations.RunPython(normalize_roles, migrations.RunPython.noop),
    ]
