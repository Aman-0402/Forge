# Forge LMS — Solution & Technical Design Document

> Source: `LMS_Solution_Document.pdf` (ARX Infotech for DSA Forge, v1.0, 14 Sep 2026).
> This file rewrites that document into an engineering reference and adds the concrete technical decisions made for this build.
> Companion files: `agent.md` (work tracker), `rule.md` (working rules), `phases/` (per-phase plans).

---

## 1. Purpose

A custom web-based Learning Management System for institutes and universities. One portal, three modules, three roles:

| Module | What it does |
|---|---|
| **Courses** | Faculty build structured courses (modules → chapters → lessons), upload content, assign work; students enroll, learn, submit, track progress. |
| **Exams** | Faculty schedule timed exams from question banks; objective questions auto-graded, subjective manually graded; results/scorecards. |
| **Coding Portal** | Faculty create programming problems with test cases; students solve in a browser editor; code runs in a sandbox and is auto-evaluated. |

| Role | Summary |
|---|---|
| **Admin** | Owns portal config. Creates/manages faculty and student accounts. Approves and oversees courses/exams/coding modules. Manages roles and permissions. Institute-wide reports. Portal-wide announcements. |
| **Faculty / Trainer** | Creates courses, modules, content. Assigns tasks. Schedules exams, builds question banks. Creates coding problems. Grades submissions. Tracks individual and batch progress. |
| **Student** | Registers, creates profile. Enrolls in assigned/available courses. Consumes content, submits assignments. Attempts exams in window. Attempts coding problems. Views results and history. |

## 2. Project Objectives (from source doc)

- Single centralized platform for course delivery, exams, coding practice/assessment.
- Admins get complete visibility and control over users, courses, institute-wide activity.
- Faculty create courses, assign tasks, schedule exams with minimal manual effort.
- Students get a simple self-service experience.
- Scalable; more modules can be added in later phases.

## 3. Functional Requirements

### 3.1 Module 1 — Courses
- Course creation with modules, chapters, lessons.
- Content formats: video, PDF, PPT, documents.
- Categorization by department, subject, level.
- Manual or auto-enrollment of students.
- Assignment creation, submission, tracking.
- Student progress tracking per course and per lesson.
- Optional: certificate generation on completion.

### 3.2 Module 2 — Exams
- Exam creation and scheduling: date, time window, duration.
- Question bank: MCQ, true/false, subjective.
- Randomized question order and option order.
- Auto-submit when time limit reached.
- Auto-grading for objective questions; manual grading workflow for subjective.
- Result and scorecard generation, visible to faculty and students.
- Basic integrity checks (tab-switch / full-screen exit detection). Scope to be finalized with client.

### 3.3 Module 3 — Coding Portal
- Faculty-created problems: description, constraints, sample test cases.
- Browser code editor, multiple languages.
- Real-time compile and execute in a sandbox.
- Automated evaluation against hidden and visible test cases.
- Submission history per student per problem.
- Optional: leaderboard.

### 3.4 Cross-cutting
- Role-based dashboards.
- In-portal notifications + email for enrollments, exam schedules, results. SMS optional.
- Audit log for key actions: exam attempts, submissions, admin changes.

## 4. Non-Functional Requirements

| Area | Requirement | How we meet it |
|---|---|---|
| Security | RBAC, encrypted credentials, secure sessions | Django password hashing (PBKDF2/Argon2), JWT access+refresh, DRF permission classes per role, HTTPS in prod |
| Scalability | Growing users/courses/exams | Stateless API (JWT), MySQL, cache layer added when needed, judge service isolated |
| Responsiveness | Desktop, tablet, mobile | React frontend; responsive UI deferred to frontend upgrade phase |
| Availability | Cloud hosted, automated backups | Docker Compose deployment, `mysqldump` cron; provider chosen at deploy phase |
| Performance | Peak load during concurrent exams | Server-side timing, minimal per-answer writes, DB indexes on attempt/answer, pagination everywhere |
| Audit & Logs | Key action logs | `AuditLog` model + DRF mixin/signals |

## 5. Out of Scope (Phase 1 per source doc)

- Native mobile apps (web is responsive instead).
- AI proctoring, plagiarism detection.
- Payment gateway.
- ERP / SIS integration.

## 6. Technology Decisions (confirmed)

| Layer | Choice | Reason |
|---|---|---|
| Backend | **Python 3.10+, Django 5.x, Django REST Framework** | Team preference (doc allows Django). Mature ORM, admin, auth. |
| Auth | **JWT — `djangorestframework-simplejwt`** | Matches doc. Stateless. Access (short) + refresh (long) tokens. |
| Database | **MySQL** (Django `mysql` backend, `mysqlclient`). Local dev server is MariaDB 12.3, db `forge_db`, utf8mb4, strict mode | User choice; doc lists MySQL. |
| Python deps | **uv** (`pyproject.toml` + `uv.lock`) | Already installed, fast, reproducible. |
| API docs | **drf-spectacular** (OpenAPI 3 + Swagger UI) | Contract for frontend; free documentation. |
| Code judge | **Judge0 CE, self-hosted via Docker Compose** | Matches doc ("Judge0-style"). Sandboxed, 60+ languages. Docker Desktop must be installed (needs WSL2 on Windows Home). |
| Cache / queue | **Deferred.** Django locmem cache now. Redis + Celery added only when a real need appears (bulk email, heavy grading, leaderboard). | YAGNI. Judge0 ships its own Redis/Postgres inside its compose. |
| File storage | Local `media/` in dev. `django-storages` + S3-compatible in prod. | Simple now; swap via settings. |
| Frontend | **React 19 + TypeScript + Vite**, `react-router-dom`, `axios`. Plain-CSS design system in `src/index.css` (Archivo / IBM Plex via Google Fonts, sidebar shell, 1450px content area, temper-colour progress bars). No UI library yet. | Doc says React. User asked for a good-looking basic UI in Phase 2; component library still deferred to Phase 5. |
| Email | Django email backend → console in dev, SMTP/SES in prod | Doc option. |
| Repo | **Monorepo**: `backend/`, `frontend/`, docs at root | Solo dev; one history. |
| Tests | `pytest` + `pytest-django` + `factory_boy` | TDD per app. |
| Lint | `ruff` (lint + format) | One fast tool. |

## 7. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Presentation: React SPA (Vite)  — Admin / Faculty / Student │
└───────────────┬──────────────────────────────────────────────┘
                │ HTTPS  JSON  (Authorization: Bearer <JWT>)
┌───────────────▼──────────────────────────────────────────────┐
│  API: Django + DRF                                            │
│  apps: accounts · courses · exams · coding · notifications ·  │
│        audit · core                                           │
└──────┬───────────────────┬───────────────────┬───────────────┘
       │                   │                   │ REST
┌──────▼──────┐   ┌────────▼────────┐  ┌───────▼─────────────┐
│ MySQL       │   │ media/ (files)  │  │ Judge0 (Docker)      │
│ core data   │   │ or S3 in prod   │  │ sandboxed execution  │
└─────────────┘   └─────────────────┘  └─────────────────────┘
```

### 7.1 Django app boundaries

| App | Owns | Depends on |
|---|---|---|
| `core` | settings helpers, base models (`TimeStampedModel`), pagination, exceptions, common permissions (`IsAdmin`, `IsFaculty`, `IsStudent`, `IsOwnerOrAdmin`) | — |
| `accounts` | `User` (custom, `role` field), `Department`, profile, admin user CRUD, JWT endpoints, registration | core |
| `courses` | `Category`, `Course`, `Module`, `Chapter`, `Lesson`, `ContentItem`, `Enrollment`, `Assignment`, `AssignmentSubmission`, `LessonProgress`, `Certificate` | accounts |
| `exams` | `QuestionBank`, `Question`, `Option`, `Exam`, `ExamQuestion`, `Attempt`, `Answer`, `IntegrityEvent`, `Result` | accounts, courses (exam may belong to a course) |
| `coding` | `Language`, `Problem`, `TestCase`, `CodeSubmission`, `TestCaseResult`, `LeaderboardEntry` (optional), Judge0 client | accounts, courses (problem may belong to a course) |
| `notifications` | `Notification` (in-portal), `Announcement`, email dispatch service | accounts |
| `audit` | `AuditLog` + helper `log_action()` | accounts |

Rule: apps talk through services/functions, not by reaching into each other's querysets from views. Cross-app foreign keys are fine.

### 7.2 Request flow (typical)

1. React sends request with `Authorization: Bearer <access>`.
2. SimpleJWT authenticates → `request.user` with `.role`.
3. DRF permission class checks role and object ownership.
4. ViewSet → serializer → service function (business logic) → model.
5. `audit.log_action()` called for key actions.
6. Response JSON. Errors follow one envelope: `{"detail": "...", "code": "...", "errors": {...}}`.

### 7.3 Key design rules

- **Custom `User` model from day one** (`AUTH_USER_MODEL = "accounts.User"`). Cannot be changed later without pain.
- **Role is a field, not a group**: `role ∈ {admin, faculty, student}`. Simple, matches doc. Django Groups can be layered later if finer permissions are needed.
- **Exam timing is server-authoritative**: `Attempt.started_at + Exam.duration` is the deadline. Answers after deadline (+ small grace) are rejected; a sweep marks overdue attempts submitted. Frontend timer is cosmetic.
- **Randomization is persisted per attempt**: question order and option order are generated at attempt start and stored on the attempt, so resume and grading are deterministic.
- **Hidden test cases never leave the server**: student serializers exclude `is_hidden=True` cases; results show pass/fail only.
- **Judge0 integration**: backend submits code + each test case (batch endpoint), stores Judge0 tokens, polls/receives callback, aggregates into `CodeSubmission.verdict`. Start with synchronous `wait=true` for simplicity; move to async + Celery if latency demands.
- **Soft-delete not used** initially; use `is_active` flags on `User`, `Course`, `Exam`, `Problem`.
- **All list endpoints paginated** (page number, default 20).
- **Every write of significance logs an audit row.**

## 8. Data Model (summary)

Full field lists live in each phase file. Key relations:

```
User(role) ─┬─< Enrollment >─ Course ─< Module ─< Chapter ─< Lesson ─< ContentItem
            ├─< LessonProgress
            ├─< AssignmentSubmission >─ Assignment ─ Course
            ├─< Attempt >─ Exam ─< ExamQuestion >─ Question ─< Option
            │      └─< Answer, IntegrityEvent
            ├─< CodeSubmission >─ Problem ─< TestCase
            │      └─< TestCaseResult
            ├─< Notification
            └─< AuditLog
Category ─< Course        Department ─< User
QuestionBank ─< Question  Language ─< CodeSubmission
```

## 9. API Surface (v1, prefix `/api/v1/`)

| Area | Endpoints (summary) |
|---|---|
| Auth | `POST auth/register/` (student self-signup) · `POST auth/token/` · `POST auth/token/refresh/` · `GET/PATCH auth/me/` · `POST auth/change-password/` |
| Users (admin) | `GET/POST users/` · `GET/PATCH/DELETE users/{id}/` (DELETE = deactivate) · `POST users/{id}/reset-password/` · `POST users/bulk-import/` · `departments/` (admin write, all read) |
| Courses | `categories/` · `courses/` · `courses/{id}/submit-for-approval/` · `approve/` · `reject/` · `archive/` · `courses/{id}/tree/` · `courses/{id}/modules/` (+`reorder/`) · `modules/{id}/chapters/` · `chapters/{id}/lessons/` · `lessons/{id}/content/` · flat `modules|chapters|lessons|content/{id}/` |
| Enrollment & progress | `courses/{id}/enroll/` · `courses/{id}/drop/` · `courses/{id}/enrollments/` (GET list, POST bulk add) · `enrollments/{id}/` (DELETE = drop) · `me/enrollments/` · `courses/{id}/progress/` · `courses/{id}/progress/me/` · `lessons/{id}/complete/` · `lessons/{id}/position/` |
| Assignments | `courses/{id}/assignments/` · `assignments/{id}/` · `assignments/{id}/submit/` · `assignments/{id}/submissions/` (`?graded=`) · `submissions/{id}/` · `submissions/{id}/grade/` |
| Exams | `question-banks/` · `question-banks/{id}/questions/` · `exams/` · `exams/{id}/questions/` · `exams/{id}/start/` · `attempts/{id}/answer/` · `attempts/{id}/submit/` · `attempts/{id}/integrity-event/` · `attempts/{id}/grade/` · `exams/{id}/results/` · `attempts/{id}/result/` |
| Coding | `languages/` · `problems/` · `problems/{id}/testcases/` · `problems/{id}/run/` (sample cases only) · `problems/{id}/submit/` · `problems/{id}/submissions/` · `submissions/{id}/` · `problems/{id}/leaderboard/` |
| Notifications | `notifications/` (`?unread=true`) · `notifications/{id}/read/` · `notifications/read-all/` · `notifications/unread-count/` · `announcements/` |
| Admin reports | `reports/overview/` · `reports/courses/` · `reports/exams/` · `audit-logs/` |
| Docs | `/api/schema/` · `/api/docs/` (Swagger UI) |

## 10. Project Layout

```
Forge/
├── Doc.md              ← this file
├── agent.md            ← work tracker (status of everything)
├── rule.md             ← working rules (commit/push, conventions)
├── CLAUDE.md           ← short pointer so every session loads the three files above
├── phases/
│   ├── PHASE-0-foundation.md
│   ├── PHASE-1-accounts-admin.md
│   ├── PHASE-2-courses.md
│   ├── PHASE-3-exams.md
│   ├── PHASE-4-coding-portal.md
│   └── PHASE-5-integration-deploy.md
├── backend/
│   ├── pyproject.toml, uv.lock
│   ├── manage.py
│   ├── config/            (settings/{base,dev,prod}.py, urls.py, asgi.py, wsgi.py)
│   ├── apps/              (core, accounts, courses, exams, coding, notifications, audit)
│   ├── media/  (gitignored)
│   ├── .env.example
│   └── tests/ or per-app tests/
├── frontend/
│   ├── package.json, vite.config.ts
│   └── src/ (api/, pages/, components/, hooks/, routes)
├── infra/
│   ├── judge0/docker-compose.yml
│   └── docker-compose.yml (full stack, Phase 5)
├── .gitignore
└── LMS_Solution_Document.pdf
```

## 11. Install List

### 11.1 System (one-time)
| Tool | Status on this machine | Action |
|---|---|---|
| Python 3.10 | installed | OK (Django 5.x supports 3.10+). Consider 3.12 later. |
| uv | installed | OK |
| Node 22 + npm | installed | OK |
| MySQL / MariaDB 12.3 | installed, running on 3306 | DB `forge_db` exists; root user (dev only) |
| Git | installed | OK |
| **Docker Desktop** | **missing** | Install before Phase 4. Windows Home → enable WSL2 first. Needed for Judge0. |
| Redis | missing | Not needed until deferred features. Will run via Docker when needed. |

### 11.2 Backend Python packages (`uv add`)
```
django
djangorestframework
djangorestframework-simplejwt
django-cors-headers
django-filter
drf-spectacular
mysqlclient
django-environ
Pillow
httpx                      # Judge0 client (Phase 4)
```
Dev group (`uv add --dev`):
```
pytest
pytest-django
factory-boy
ruff
```
Later (only when needed): `celery`, `redis`, `django-redis`, `django-storages`, `boto3`, `gunicorn`, `whitenoise`, `reportlab` or `weasyprint` (certificates).

### 11.3 Frontend packages (`npm i`)
```
react react-dom react-router-dom axios
```
Dev: Vite scaffold (`npm create vite@latest frontend -- --template react-ts`), `typescript`, `@types/react`, `@types/react-dom`.
Later (upgrade phase): `@tanstack/react-query`, `tailwindcss`, `@monaco-editor/react` (code editor), UI kit.

### 11.4 Infra
- Judge0 CE `docker-compose.yml` (official release bundle) under `infra/judge0/`.

## 12. Timeline Mapping

Source doc proposes 4 weeks. Our phase order is backend-first:

| Source week | Our phase(s) |
|---|---|
| Week 1 Foundation & Admin | Phase 0 + Phase 1 |
| Week 2 Courses | Phase 2 |
| Week 3 Exams + Coding start | Phase 3 + Phase 4 (start) |
| Week 4 Coding, integration, go-live | Phase 4 + Phase 5 |

## 13. Assumptions & Open Questions

- Supported languages for Coding Portal: start with Python, C, C++, Java, JavaScript (Judge0 IDs). Final list pending client.
- Integrity checks: log tab-switch/full-screen-exit events; no auto-fail. Client to confirm policy.
- Student self-registration is allowed (doc says students "register"); admin can disable via a setting.
- Certificates and leaderboard are optional; scheduled last inside their phases.
- Email provider (SMTP vs SES) and cloud provider decided at Phase 5.
- SMS not implemented in Phase 1 scope.
