# ProDUS Assistants Time Registration Backend

Backend service for **ProDUS Registro de Horas**. It provides a Django REST API for user and assistant administration, work-session tracking, schedules, projects, institute-network access control, and automated closing of open time logs.

## Contents

- [System overview](#system-overview)
- [Technology stack](#technology-stack)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Database setup](#database-setup)
- [Running the application](#running-the-application)
- [API documentation and main endpoints](#api-documentation-and-main-endpoints)
- [Application modules](#application-modules)
- [Automation](#automation)
- [Testing and maintenance](#testing-and-maintenance)
- [Production notes](#production-notes)

## System overview

The backend is a Django project exposed as a REST API. The frontend authenticates with JWT tokens and uses the API to manage assistants and their work sessions.

The main workflow is:

1. A user signs in through the JWT login endpoint.
2. The client sends the access token in the `Authorization` header:
   `Authorization: Bearer <access-token>`.
3. An assistant starts a work session. The API creates a time log with a check-in timestamp.
4. The assistant can query the current open session and close it when work ends.
5. Time logs may be associated with projects and include activities, descriptions, breaks, statuses, and manager/approval information.
6. A scheduled automation job can close time logs that remain open according to the business rules.

The application uses Costa Rica time (`America/Costa_Rica`) and PostgreSQL as its primary database. Django admin is available for administrative data management, and Swagger/ReDoc expose the API schema.

## Technology stack

- Python 3.12 or newer
- Django 6.x
- Django REST Framework
- PostgreSQL 15
- Simple JWT for authentication
- `django-cors-headers` for frontend access
- `drf-yasg` for Swagger/OpenAPI documentation
- WhiteNoise for static files
- Docker Compose (optional, for PostgreSQL)

## Requirements

Install the following before starting:

- Python 3.12+
- pip and `venv`
- PostgreSQL 15+, or Docker Desktop with Docker Compose
- Git

On Linux production hosts, the automation scripts also require Bash and `cron`/`crontab`.

## Installation

From the repository root, create and activate a virtual environment.

### Windows PowerShell

```powershell
cd C:\path\to\ProDUS_Registro_de_Horas_Backend\backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, either allow scripts for the current user or run the commands through the Python executable directly:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### Linux/macOS

```bash
cd /path/to/ProDUS_Registro_de_Horas_Backend/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Configuration

The settings module looks for environment files in `backend/.env` and in the repository root. Start from the provided template:

```powershell
# Windows PowerShell, from backend/
Copy-Item .env.example .env
```

```bash
# Linux/macOS, from backend/
cp .env.example .env
```

Review every value in `.env` and replace example credentials and keys with environment-specific values.

Important settings include:

| Variable | Purpose | Example |
| --- | --- | --- |
| `DEBUG` | Enables Django debug behavior | `True` locally, `False` in production |
| `SECRET_KEY` | Signs Django and JWT data | A long, random private value |
| `ALLOWED_HOSTS` | Comma-separated accepted hostnames/IPs | `localhost,127.0.0.1` |
| `DB_ENGINE` | Django database engine | `django.db.backends.postgresql` |
| `DB_NAME` | PostgreSQL database name | `produs_db` |
| `DB_USER` / `DB_PASSWORD` | PostgreSQL credentials | Local or deployment-specific values |
| `DB_HOST` / `DB_PORT` | PostgreSQL connection address | `localhost` / `5432` |
| `CORS_ALLOWED_ORIGINS` | Frontend origins allowed by CORS | `http://localhost:5173` |
| `CSRF_TRUSTED_ORIGINS` | Trusted browser origins | `http://localhost:5173` |
| `JWT_ACCESS_TOKEN_LIFETIME_HOURS` | Access-token lifetime | `8` |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | Refresh-token lifetime | `7` |
| `USE_HTTPS` | Enables HTTPS-related settings | `False` locally |

For a local installation, a minimal `.env` can use:

```dotenv
DEBUG=True
SECRET_KEY=replace-this-with-a-local-secret
ALLOWED_HOSTS=localhost,127.0.0.1

DB_ENGINE=django.db.backends.postgresql
DB_NAME=produs_db
DB_USER=produs_user
DB_PASSWORD=replace-this-password
DB_HOST=localhost
DB_PORT=5432

CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
JWT_ACCESS_TOKEN_LIFETIME_HOURS=8
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7
USE_HTTPS=False
```

## Database setup

#### Option A: PostgreSQL with Docker Compose

The Compose file starts PostgreSQL only; Django itself is run from the virtual environment.

1. Create and edit `backend/.env`.
2. Ensure `DB_NAME`, `DB_USER`, `DB_PASSWORD`, and `DB_PORT` are set.
3. Start PostgreSQL from `backend/`:

```powershell
docker compose up -d db
docker compose ps
```

The database is persisted in the `postgres_data` Docker volume. Stop the container without deleting data with:

```bash
docker compose down
```

Do not use `docker compose down -v` unless you intentionally want to delete the database volume.

#### Option B: Existing PostgreSQL installation

Create a PostgreSQL database and user matching the values in `.env`, then make sure the database server is reachable at `DB_HOST:DB_PORT`. No Docker command is required in this setup.

### Apply migrations and create an administrator

From `backend/`, with the virtual environment active:

```bash
python manage.py migrate
python manage.py createsuperuser
```

On Windows, use the same commands in PowerShell. The custom user model uses `username` as its login field.

## Running the application

From the `backend/` directory:

```bash
python manage.py runserver
```

The development server is available at <http://127.0.0.1:8000/>.

Useful commands:

```bash
python manage.py check
python manage.py collectstatic --noinput
python manage.py test
```

For a production WSGI server, install/use Gunicorn on Linux and configure the bind address and worker count using the deployment environment. The provided `.env.example` includes `GUNICORN_WORKERS` and `GUNICORN_BIND` for that deployment setup.

## API documentation and main endpoints

When the server is running:

- API root: <http://127.0.0.1:8000/api/>
- Swagger UI: <http://127.0.0.1:8000/swagger/>
- ReDoc: <http://127.0.0.1:8000/redoc/>
- OpenAPI JSON/YAML: `/swagger.json` and `/swagger.yaml`
- Django admin: <http://127.0.0.1:8000/admin/>

All API endpoints require authentication by default unless explicitly marked public. Obtain a token:

```http
POST /api/users/auth/login/
Content-Type: application/json

{
  "username": "your-user",
  "password": "your-password"
}
```

Use the returned access token on protected requests:

```http
Authorization: Bearer <access-token>
```

Main route groups:

| Route | Purpose |
| --- | --- |
| `/api/users/auth/login/` | Obtain access and refresh JWT tokens |
| `/api/users/auth/refresh/` | Refresh an access token |
| `/api/users/auth/logout/` | Log out and invalidate the refresh token |
| `/api/users/auth/me/` | Retrieve the authenticated user |
| `/api/users/auth/validate-institute-ip/` | Validate access from an institute IP |
| `/api/users/users/` | User administration |
| `/api/users/assistants/` | Create and list assistants |
| `/api/users/allowed-ip-ranges/` | Manage allowed IP ranges |
| `/api/timelogs/work-session/start/` | Start a work session |
| `/api/timelogs/work-session/current/` | Retrieve the current open session |
| `/api/timelogs/work-session/close/` | Close a work session |
| `/api/projects/active/` | List active projects |
| `/api/projects/coordinators/active/` | List active coordinators |
| `/api/schedules/create/` | Create an assistant schedule |

The Swagger schema is the authoritative source for request bodies, response formats, and permissions for each endpoint.

## Application modules

- **`apps.users`**: custom users, roles, assistants, JWT authentication, password changes, and allowed IP ranges.
- **`apps.time_logs`**: work-session start/current/close operations and time-log status, activity, break, project, and approval data.
- **`apps.projects`**: projects and coordinator/assistant assignments.
- **`apps.schedules`**: date ranges and non-overlapping weekly schedule blocks for assistants.
- **`apps.ip_control`**: authorized IPs and temporary IP exceptions.
- **`core`**: shared exceptions, pagination, permissions, and validators.
- **`automation`**: shell scripts and cron configuration for recurring jobs.

The database schema is managed through Django migrations in each app's `migrations/` directory. After pulling code that changes models, run:

```bash
python manage.py migrate
```

## Automation

The automation runner is intended for Linux hosts and uses `crontab`. Its current job closes open time logs:

`backend/automation/jobs/close_open_time_logs.bash`

From `backend/automation`:

```bash
./list_jobs.bash
./set_schedule.bash close_open_time_logs "0 0 * * *"
./enable_job.bash close_open_time_logs
./run_job.bash close_open_time_logs
./run_enabled.bash
./disable_job.bash close_open_time_logs
```

Automation state is stored in `enabled/`, schedules in `schedules/`, and logs in `logs/`. Make sure the job's environment, working directory, virtual environment, and database access are available to the cron process. See [`backend/automation/README.md`](backend/automation/README.md) for the complete runner reference.

## Testing and maintenance

Run the full Django test suite:

```bash
python manage.py test
```

Run checks before deploying:

```bash
python manage.py check --deploy
python manage.py collectstatic --noinput
```

After updating dependencies:

```bash
python -m pip install -r requirements.txt
```

The repository also includes `rebuild_backend.sh` and `pull_and_rebuild_backend.sh` for the Linux service deployment workflow. These scripts install dependencies, apply migrations, collect static files, and restart the `produs-backend` systemd service. Review their paths and service configuration before using them on another host.

## Production notes

- Set `DEBUG=False`.
- Use a unique, secret `SECRET_KEY`.
- Set `ALLOWED_HOSTS` to the actual backend hostnames/IPs.
- Use strong database credentials and restrict PostgreSQL network access.
- Configure HTTPS and set `USE_HTTPS=True` when TLS is terminated for this application.
- Set `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` to explicit frontend origins. Do not rely on permissive development settings.
- Run migrations and `collectstatic` during deployment.
- Use a process manager such as systemd and a reverse proxy such as Nginx or Apache.
- Back up the PostgreSQL database and monitor the automation logs.
