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

## Exams (`/api/v1/`)
| Method | Path | Who | Notes |
|---|---|---|---|
| CRUD | `question-banks/` | faculty, admin | Faculty see own + shared banks; only owner/admin edit. |
| POST | `question-banks/{id}/import/` | owner, admin | `{questions: [...]}`, all-or-nothing. |
| GET / POST | `question-banks/{id}/questions/` | readers / owner | Filters `type`, `difficulty`, `is_active`, `tag`, `search`. Options inline with `is_correct`. |
| GET / PATCH / DELETE | `questions/{id}/` | readers / owner | Locked (except `is_active`) once attempted; cannot delete if in an exam. |
| CRUD | `exams/` | staff; students list eligible exams | Students get `phase` and `my_attempts`. |
| GET / POST | `exams/{id}/questions/` | managers | POST `{question_ids}` or `{bank, count, difficulty, type}`. |
| PATCH / DELETE | `exams/{id}/questions/{row}/` | managers | `marks_override`. Locked once attempted. |
| POST | `exams/{id}/schedule/`, `unschedule/`, `extend/` (`{ends_at}`), `close/`, `release-results/` | managers | Close auto-submits in-progress attempts. |
| POST | `exams/{id}/start/` | eligible student | 201 new attempt, 200 resume. Never includes answer key. |
| GET | `attempts/{id}/` | owner | Questions in the student's order with saved answers and `seconds_remaining`. |
| PUT | `attempts/{id}/answers/{exam_question_id}/` | owner | `{selected_option_ids}` or `{text_answer}`. Rejected after deadline + grace. |
| POST | `attempts/{id}/submit/`, `attempts/{id}/integrity-events/` | owner | |
| GET | `exams/{id}/attempts/` | managers | `?status=`; includes `integrity_event_count`. |
| GET | `attempts/{id}/review/` | managers | Full answer key and integrity events. |
| PATCH | `answers/{id}/grade/` | managers | Written answers only: `{marks_awarded, grader_feedback}`. |
| GET | `attempts/{id}/result/` | owner (when released), managers | Answers revealed only if `reveal_answers`. |
| GET | `exams/{id}/results/`, `exams/{id}/results/export/` | managers | Stats + rows; CSV. |
| GET | `me/results/` | student | Scores hidden until visible. |

## Coding portal (`/api/v1/`)
| Method | Path | Who | Notes |
|---|---|---|---|
| GET | `languages/` | any | Enabled languages with `editor_mode` and starter template. |
| CRUD | `problems/` | staff write; students see open problems | Filters `difficulty`, `status`, `course`, `tag`, `search`. Students get `my_status`. |
| POST | `problems/{id}/publish/`, `unpublish/`, `archive/` | managers | Publish needs a test case; notifies enrolled students for course problems. |
| GET / POST | `problems/{id}/testcases/`, `problems/{id}/testcases/import/` | managers | Samples cannot be hidden. |
| PATCH / DELETE | `testcases/{id}/` | managers | Changes are audited. |
| POST | `problems/{id}/run/` | students (open problems), managers | `{language, source_code, stdin?}`. Without `stdin`, runs sample cases. Not stored. 10/min. |
| POST | `problems/{id}/submit/` | students | Judges every test case. 5/min. 503 if Judge0 is down (submission kept as error). |
| GET | `problems/{id}/submissions/`, `code-submissions/{id}/` | owner; managers see all | Hidden case input/output only for managers. |
| POST | `problems/{id}/rejudge/` | managers | Re-runs all submissions. |
| GET | `problems/{id}/leaderboard/`, `me/coding/summary/` | viewers / student | |

Judge0 settings in `.env`: `JUDGE0_URL`, `JUDGE0_AUTH_TOKEN`, `JUDGE0_TIMEOUT_SECONDS`. Setup: `infra/judge0/README.md`. Check a live instance with `uv run python manage.py judge0_check`.

Demo data: `seed_demo_problems` (after `seed_demo_courses`) seeds languages and four problems.

Scheduled jobs for production: `uv run python manage.py sweep_overdue_attempts` every minute.

Demo data: `seed_demo_exams` (after `seed_demo_courses`) creates bank "DSA fundamentals", a live exam "DSA quiz 1" and a closed, graded, released "DSA diagnostic test".

Concurrency check (DEBUG only, against a running server): `uv run python manage.py exam_load_check --students 200`.

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
