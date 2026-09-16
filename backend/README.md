# Forge LMS — Backend

Django 5 + Django REST Framework + SimpleJWT, MySQL (MariaDB locally), managed with `uv`.

## Setup (Windows, PowerShell)

```powershell
cd backend
uv sync                                 # create .venv and install deps
Copy-Item .env.example .env             # then set SECRET_KEY and DATABASE_URL
uv run python manage.py migrate
uv run python manage.py seed_dev        # dev users (see below)
uv run python manage.py runserver       # http://localhost:8000
```

Database: `DATABASE_URL=mysql://root:@127.0.0.1:3306/forge_db`. The DB must exist. The DB user needs rights to create `test_forge_db` for pytest.

## Useful URLs
- Swagger UI: http://localhost:8000/api/docs/
- OpenAPI schema: http://localhost:8000/api/schema/
- Django admin: http://localhost:8000/admin/

## Dev users (`seed_dev`, never run in production)
| Role | Email | Password |
|---|---|---|
| admin | admin@forge.local | Admin@12345 |
| faculty | faculty1@forge.local, faculty2@forge.local | Faculty@12345 |
| student | student1..5@forge.local | Student@12345 |

## Tests and lint
```powershell
uv run pytest
uv run ruff check . ; uv run ruff format .
```

## Auth endpoints (`/api/v1/`)
| Method | Path | Notes |
|---|---|---|
| POST | `auth/register/` | Student self-registration. Role input ignored. |
| POST | `auth/token/` | `{email, password}` → `{access, refresh}` |
| POST | `auth/token/refresh/` | `{refresh}` → `{access, refresh}` (rotated) |
| POST | `auth/logout/` | `{refresh}` → 205, refresh token blacklisted |
| GET/PATCH | `auth/me/` | Current user. Email and role read-only. |
| POST | `auth/change-password/` | `{old_password, new_password}` → 204 |

Errors use one envelope: `{"detail": "...", "code": "...", "errors": {...}}`.

## Layout
```
config/settings/{base,dev,prod}.py   settings (env via django-environ)
apps/core/        TimeStampedModel, role permissions, pagination, error handler
apps/accounts/    User (email login, role), Department, auth API, seed_dev
conftest.py       api_client, admin_user, faculty_user, student_user, auth_client
```
