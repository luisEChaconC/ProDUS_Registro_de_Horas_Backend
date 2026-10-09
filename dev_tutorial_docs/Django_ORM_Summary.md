# Summary: Django ORM, SQL, and architecture

## 1) What is the Django ORM?
The ORM (Object-Relational Mapper) allows you to work with the database using Python classes (models) instead of writing SQL directly. Django translates those operations into PostgreSQL-compatible SQL.

**Advantages**
- Fewer errors and better security (reduces the risk of SQL injection).
- Cleaner and more maintainable code.
- Automatic migrations for versioning database changes.
- Portability (although this project always uses PostgreSQL).

## 2) How does Django name SQL objects?
In Django, the table name is defined in the model with `db_table`:

```py
class User(models.Model):
    class Meta:
        db_table = 'user'
```

If `db_table` is not defined, Django uses `appname_modelname`.

**Column names**
Each model attribute becomes a column. For example:

```py
username = models.CharField(max_length=255)
```

generates a `username` column in the table.

## 3) How is the ORM used?
Basic examples:

```py
# Create
User.objects.create_user(username='juan', password='123')

# Read
User.objects.get(username='juan')
User.objects.filter(is_active=True)

# Update
User.objects.filter(id=1).update(is_active=False)

# Delete
User.objects.filter(id=1).delete()
```

## 4) How are new changes (migrations) generated?
Whenever you change a model:

1. **Create a migration**
   ```bash
   python manage.py makemigrations
   ```

2. **Apply the migration**
   ```bash
   python manage.py migrate
   ```

Django stores these changes in files inside `migrations/` and keeps the migration history in the `django_migrations` table.

## 5) Current project architecture (summary)

### Backend (Django)
- **apps/users**: users, people, and assistants.
- **apps/authentication_authorization**: allowed IP ranges (AllowedIPRange).
- **apps/schedules**: schedules.
- **apps/activities**: activities.
- **apps/reports**: reports.
- **core/**: permissions, validators, pagination, and exceptions.

**IP flow**
- The backend validates IPs with `IsFromInstitute`.
- Allowed ranges are stored in the database (AllowedIPRange) and validated with CIDR.
- In development mode (`ALLOW_ALL_IPS=True`), all IPs are allowed.

### Frontend (Vue + Vite)
- **router**: uses a guard to block access when the IP is invalid.
- **views**: `LoginView`, `HomeView`, `BlockedView`.
- **services/api.ts**: handles login, token refresh, and IP validation.

## 6) When should raw SQL be used?
Only when the ORM is not sufficient (complex queries or special reports). Even so, the ORM covers nearly everything this system needs.

```py
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT * FROM user WHERE is_admin = %s", [True])
    rows = cursor.fetchall()
```

## 7) Practical recommendation
- Use the ORM for normal operations.
- Change models and generate migrations.
- Avoid raw SQL unless it is genuinely necessary.
