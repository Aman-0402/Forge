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

## Admin, notifications and announcements (`/api/v1/`)
| Method | Path | Who | Notes |
|---|---|---|---|
| GET/POST | `users/` | admin | Filters `role`, `department`, `is_active`, `search`. Create without `password` returns `temp_password`. |
| GET/PATCH/DELETE | `users/{id}/` | admin | DELETE deactivates and revokes tokens. Admins cannot demote or deactivate themselves. |
| POST | `users/{id}/reset-password/` | admin | Returns `temp_password`. |
| POST | `users/bulk-import/` | admin | Multipart `file` (CSV). Columns: `email`, `role` required; `first_name`, `last_name`, `phone`, `department_code`, `roll_number`, `batch`, `year`, `employee_id`, `designation` optional. |
| GET / POST, PATCH, DELETE | `departments/` | any / admin | |
| GET | `audit-logs/` | admin | Filters `actor`, `action`, `target_type`, `target_id`, `created_after`, `created_before`. |
| GET | `notifications/` | own | `?unread=true`, `?kind=` |
| POST | `notifications/{id}/read/`, `notifications/read-all/` | own | |
| GET | `notifications/unread-count/` | own | |
| GET / POST, PATCH, DELETE | `announcements/` | any / admin, faculty | Audience `all`, `faculty`, `students`, `department`. Faculty: own department only, own posts only. |

## Courses (`/api/v1/`)
| Method | Path | Who | Notes |
|---|---|---|---|
| GET / POST | `courses/` | any / admin, faculty | Filters `status`, `level`, `categories`, `department`, `instructor`, `search`. Faculty become instructor; admins must pass `instructor`. |
| GET / PATCH / DELETE | `courses/{id}/` | visible / managers | DELETE only for drafts without enrollments. |
| POST | `courses/{id}/submit-for-approval/`, `archive/` | managers | |
| POST | `courses/{id}/approve/`, `reject/` (`{reason}`) | admin | Approve also runs automatic enrollment. |
| GET | `courses/{id}/tree/` | visible | Whole outline; non-preview lessons locked unless enrolled or manager. |
| GET / POST | `courses/{id}/modules/`, `modules/{id}/chapters/`, `chapters/{id}/lessons/`, `lessons/{id}/content/` | visible / managers | Content is multipart for files. Kinds: `video`, `pdf`, `ppt`, `doc`, `link`, `text`. |
| POST | `.../reorder/` with `{ids: [...]}` | managers | Must list every child once. |
| GET / PATCH / DELETE | `modules/{id}/`, `chapters/{id}/`, `lessons/{id}/`, `content/{id}/` | visible / managers | |
| POST | `courses/{id}/enroll/`, `courses/{id}/drop/` | student | Open courses only. |
| GET / POST | `courses/{id}/enrollments/` | managers | POST `{student_ids, batch, department}`. |
| DELETE | `enrollments/{id}/` | managers | Marks dropped. |
| GET | `me/enrollments/` | student | `?status=` |
| POST | `lessons/{id}/complete/`, `lessons/{id}/position/` (`{seconds}`) | enrolled student | |
| GET | `courses/{id}/progress/`, `courses/{id}/progress/me/` | managers / enrolled student | |
| GET / POST | `courses/{id}/assignments/` | enrolled, managers / managers | Multipart with optional `attachment`. |
| GET / PATCH / DELETE | `assignments/{id}/` | enrolled / managers | |
| POST | `assignments/{id}/submit/` | enrolled student | `file` and/or `text`; resubmit until graded. |
| GET | `assignments/{id}/submissions/` | managers (all), student (own) | `?graded=true|false` |
| GET / POST | `submissions/{id}/`, `submissions/{id}/grade/` (`{marks, feedback}`) | owner, managers / managers | |
| CRUD | `categories/` | any read, admin write | |

Managers = admin, course instructor or co-instructor.

Demo data: `uv run python manage.py seed_demo_courses` (after `seed_dev`) creates DSA101, PY110, DB220 (published) and ML300 (draft) with lessons, enrollments, progress and assignments.

Example CSV for bulk import:
```csv
email,first_name,last_name,role,department_code,roll_number,employee_id
asha@college.edu,Asha,K,student,CSE,CSE-001,
farid@college.edu,Farid,M,faculty,CSE,,EMP-12
```

## Layout
```
config/settings/{base,dev,prod}.py   settings (env via django-environ)
apps/core/           TimeStampedModel, role permissions, pagination, error handler
apps/accounts/       User (email login, role), Department, Student/Faculty profiles,
                     auth API, admin user management (user_admin.py), seed_dev
apps/audit/          AuditLog, log_action(), AuditedModelMixin
apps/notifications/  Notification + notify(), Announcement audience rules
conftest.py       api_client, admin_user, faculty_user, student_user, auth_client
```
