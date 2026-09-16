# Phase 1 — Accounts & Admin

**Goal:** Admin can fully manage users, roles, and departments through the API. Audit logging and in-portal announcements/notifications exist as a base for later modules. Minimal admin frontend pages to exercise it.

**Maps to source doc:** Week 1 (Admin panel: user and role management). Role table §5.

**Depends on:** Phase 0.

**Estimated effort:** 2 days.

## Data model

### accounts
| Model | Fields |
|---|---|
| `Department` | `name` (unique), `code` (unique), `description`, timestamps |
| `User` (from Phase 0) | + `is_active` handling, `must_change_password` (bool, set when admin creates account), `last_login_ip` (optional) |
| `StudentProfile` | `user` O2O, `roll_number` (unique, nullable), `batch` (char), `year` (int), `bio` |
| `FacultyProfile` | `user` O2O, `employee_id` (unique, nullable), `designation`, `bio` |

Profiles created via signal on user create based on role.

### audit
| Model | Fields |
|---|---|
| `AuditLog` | `actor` FK User (nullable for system), `action` (char, e.g. `user.create`, `exam.attempt.submit`), `target_type` (char), `target_id` (char), `metadata` (JSONField), `ip`, `created_at` |

Service: `log_action(actor, action, target=None, metadata=None, request=None)`.

### notifications
| Model | Fields |
|---|---|
| `Notification` | `recipient` FK, `title`, `body`, `kind` (enum: info/enrollment/exam/result/assignment/coding/announcement), `link` (char), `is_read`, `read_at`, timestamps |
| `Announcement` | `author` FK, `title`, `body`, `audience` (enum: all/faculty/students/department/course), `department` FK null, `course` FK null (added in Phase 2), `published_at`, `expires_at`, timestamps |

Service: `notify(users, title, body, kind, link=None, email=False)` creates rows and optionally sends email (console backend in dev).

## API

| Method | Path | Role | Notes |
|---|---|---|---|
| GET/POST | `users/` | admin | filters: `role`, `department`, `is_active`, `search` (name/email/roll) |
| GET/PATCH/DELETE | `users/{id}/` | admin | DELETE = set `is_active=False` |
| POST | `users/{id}/reset-password/` | admin | generates temp password, sets `must_change_password`, notifies |
| POST | `users/bulk-import/` | admin | CSV upload: email, first_name, last_name, role, department_code, roll_number |
| GET/POST | `departments/` · `departments/{id}/` | admin write, all read | |
| GET/PATCH | `auth/me/` | any | includes nested profile |
| GET | `audit-logs/` | admin | filters: actor, action, date range |
| GET | `notifications/` | any (own) | `?unread=true` |
| POST | `notifications/{id}/read/` · `notifications/read-all/` | any (own) | |
| GET/POST/PATCH/DELETE | `announcements/` | admin+faculty write (faculty only course/department scoped), all read | list filtered by audience |

## Checklist
- [x] Models + migrations for `Department`, profiles, `AuditLog`, `Notification`, `Announcement`. Data migration backfills profiles for existing users.
- [x] `apps.audit.services.log_action` + DRF mixin (`apps.audit.mixins.AuditedModelMixin`) that logs create/update/destroy.
- [x] `apps.notifications.services.notify` + email helper (`send_mass_mail`, console backend in dev; failures logged, never break the request).
- [x] Admin user CRUD ViewSet with filters and search; soft deactivate that also revokes refresh tokens.
- [x] Reset-password and bulk CSV import actions (validate rows, return per-row errors). Services in `apps/accounts/user_admin.py`.
- [x] Profile serializers nested in `me` (users may edit `bio` only).
- [x] Announcements ViewSet with audience filtering in `get_queryset`. `course` audience deferred to Phase 2.
- [x] Tests: role matrix for every endpoint (admin 200, faculty 403, student 403, anon 401); bulk import happy + invalid rows; audit rows created on user create/update; notification read flow; announcement visibility by audience.
- [x] Frontend (minimal): `/admin/users` table with create/edit/deactivate/reset/bulk import; `/admin/departments`; `/admin/audit-logs`; `/notifications` with unread badge; `/announcements` list + post; `/change-password` forced when `must_change_password`.
- [x] Update `agent.md`; commit + push per feature.

## As built (differences from plan)
- Extra endpoint `GET notifications/unread-count/` for the nav badge.
- Extra notification kind `account` for credential messages.
- Faculty may post only `audience=department` for their own department, and may edit/delete only their own posts.
- Announcements scheduled in the future are not delivered when they go live yet. Needs a scheduler (Phase 5).
- `must_change_password` is enforced by the frontend only. The API does not block other calls yet.
- Temporary passwords are returned to the admin in the API response and emailed in plain text. Replace with one-time set-password links in Phase 5 hardening.
- After deactivation or reset, refresh tokens are revoked immediately. Access tokens stop working at once on deactivation; after a reset an old access token stays valid until it expires (max 30 min).

## Definition of done
- Admin can create a faculty and a student, they can log in, `me` returns correct role and profile.
- Audit log lists those actions.
- Announcement posted by admin visible to students; faculty-only announcement invisible to students.
- Tests green, pushed.
