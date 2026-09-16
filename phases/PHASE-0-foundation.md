# Phase 0 — Foundation

**Goal:** A running Django API with JWT auth, a custom User model with roles, MySQL connected, OpenAPI docs served, tests green, and a bare React app that can log in and show "who am I". Everything committed and pushed.

**Maps to source doc:** Week 1 (Foundation, authentication and access-control framework).

**Estimated effort:** 1–2 days.

## Prerequisites
- [x] MySQL-compatible server running (MariaDB 12.3 on 3306). DB `forge_db` exists; dev user `root` with empty password. `DATABASE_URL=mysql://root:@127.0.0.1:3306/forge_db`. Test DB `test_forge_db` is created by pytest.
- [ ] (Optional now, required by Phase 4) Install Docker Desktop with WSL2 backend.

## Checklist

### 0.1 Repo scaffolding
- [x] `backend/`, `frontend/`, `infra/` directories.
- [x] `.gitignore` (done at bootstrap).
- [x] `backend/.env.example` with `SECRET_KEY`, `DEBUG`, `DATABASE_URL`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `JUDGE0_URL`, `EMAIL_*`.

### 0.2 Backend project
- [x] `cd backend; uv init --python 3.10` → `pyproject.toml`.
- [x] `uv add django djangorestframework djangorestframework-simplejwt django-cors-headers django-filter drf-spectacular mysqlclient django-environ Pillow`
- [x] `uv add --dev pytest pytest-django factory-boy ruff`
- [x] `uv run django-admin startproject config .`
- [x] Split settings: `config/settings/__init__.py`, `base.py`, `dev.py`, `prod.py`. `manage.py` defaults to `config.settings.dev`.
- [x] `base.py`: `INSTALLED_APPS` (rest_framework, rest_framework_simplejwt, rest_framework_simplejwt.token_blacklist, corsheaders, django_filters, drf_spectacular, apps.core, apps.accounts), `AUTH_USER_MODEL = "accounts.User"`, `DATABASES` from `DATABASE_URL`, `REST_FRAMEWORK` defaults (JWT auth, `IsAuthenticated`, PageNumberPagination size 20, `AutoSchema` from spectacular, `DjangoFilterBackend`), `SIMPLE_JWT` (access 30 min, refresh 7 days, rotate + blacklist), `SPECTACULAR_SETTINGS`, `MEDIA_ROOT/URL`, `CORS_ALLOWED_ORIGINS`.
- [x] `apps/` package. `apps/core/`: `models.py` (`TimeStampedModel` abstract with `created_at`, `updated_at`), `permissions.py` (`IsAdmin`, `IsFaculty`, `IsStudent`, `IsAdminOrFaculty`, `IsOwnerOrAdmin`), `pagination.py`, `exceptions.py` (custom exception handler → uniform envelope).
- [x] `apps/accounts/`: `User(AbstractUser)` with `role` (choices admin/faculty/student, default student), `email` unique + used as `USERNAME_FIELD`, `phone`, `avatar`, `department` FK (nullable; `Department` model lives here too). Custom `UserManager`.
- [x] `apps/accounts` endpoints: `POST auth/register/` (student only), `POST auth/token/`, `POST auth/token/refresh/`, `POST auth/logout/` (blacklist refresh), `GET/PATCH auth/me/`, `POST auth/change-password/`.
- [x] `config/urls.py`: `/admin/`, `/api/v1/` includes, `/api/schema/`, `/api/docs/`, media in dev.
- [x] `uv run python manage.py makemigrations accounts && migrate`.
- [x] `createsuperuser` (role must be admin → override in manager or set after). Done via `create_superuser` defaulting role=admin; `seed_dev` creates admin@forge.local.
- [x] Management command `seed_dev` creating 1 admin, 2 faculty, 5 students (idempotent).
- [x] `pytest.ini` / `[tool.pytest.ini_options]` with `DJANGO_SETTINGS_MODULE=config.settings.dev`. `conftest.py` with `api_client`, `admin_user`, `faculty_user`, `student_user`, `auth_client(user)` fixtures. `factories.py` with `UserFactory`.
- [x] Tests: register creates student role only; token obtain/refresh; `me` requires auth; `change-password` validates old password; inactive user cannot log in.
- [x] `ruff` config in `pyproject.toml` (line length 100, select E,F,I,B,UP).

### 0.3 Frontend (minimal)
- [ ] `npm create vite@latest frontend -- --template react-ts`; `npm i react-router-dom axios`.
- [ ] `src/api/client.ts`: axios instance, base URL from `VITE_API_URL`, request interceptor adds Bearer, response interceptor refreshes on 401 once.
- [ ] `src/auth/`: `AuthContext` (user, login, logout, loading), `RequireAuth` route guard, `RequireRole`.
- [ ] Pages: `/login`, `/register`, `/me` (shows user JSON + role), role-based landing stubs `/admin`, `/faculty`, `/student`.
- [ ] `.env.example` with `VITE_API_URL=http://localhost:8000/api/v1`.

### 0.4 Docs and commit
- [ ] `backend/README.md` with setup commands.
- [ ] Update `agent.md` (Phase 0 done, decisions, deviations).
- [ ] Commits (examples): `chore: scaffold django backend with uv`, `feat(accounts): custom user model with roles`, `feat(accounts): jwt auth endpoints`, `test(accounts): auth flows`, `chore(frontend): vite react scaffold with auth`, `docs: update agent.md after phase 0`. Push after each.

## Definition of done
- `uv run pytest` green.
- `GET /api/docs/` renders Swagger with auth endpoints.
- Frontend logs in as seeded admin and shows role.
- All pushed to `origin main`.
