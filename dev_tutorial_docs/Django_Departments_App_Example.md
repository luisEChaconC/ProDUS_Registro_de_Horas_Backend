# Example: Django "departments" app for database-only data

## 1. When should you create an app?
- When you have a clear feature or business domain (users, reports, activities, departments, and so on).
- Each app is an independent module and can contain models, business logic, endpoints, and more.

## 2. When should you create only a table without business logic?
- When you only need to store simple information (catalogs, lists, or configuration) and there are no related rules or processes.
- Examples: activities, departments, document types, countries, and so on.
- You do not need to create views, serializers, services, or URLs if you will not expose the table through the API or add extra logic.

---

## 3. Complete example: "departments" app

### a) Create the app
```bash
python manage.py startapp departments
```

### b) Define the model in departments/models.py
```python
from django.db import models

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
```

### c) Register the app in settings.py
Add `'apps.departments',` to the `INSTALLED_APPS` list.

### d) Create and apply the migration
```bash
python manage.py makemigrations departments
python manage.py migrate
```

### e) (Optional) Register it in admin.py
```python
from django.contrib import admin
from .models import Department

admin.site.register(Department)
```

---

## 4. Recommended internal structure for a Django app

- models.py: Entity/table definitions
- admin.py: Administration panel configuration
- views.py: Endpoints/controllers (only when there is an API)
- serializers.py: Data transformation (only when there is an API)
- services.py: Business logic (only when there are rules/processes)
- urls.py: Routes (only when there is an API)
- tests.py: Tests

---

## 5. Summary
- If you only need the table, define the model in models.py and register the app in `INSTALLED_APPS`.
- If you need business logic or endpoints later, you can add the corresponding files.
- This keeps the structure clean and simple.