# Forge LMS — Agent Work Tracker

> Single source of truth for project status. Update at start and end of every work session (see `rule.md` §2).
> Design: `Doc.md`. Rules: `rule.md`. Phase plans: `phases/`.

**Last updated:** 2026-09-16
**Current phase:** Phase 2 — Courses (next up). Phases 0 and 1 done.
**Repo:** https://github.com/Aman-0402/Forge.git (branch `main`)

---

## Status legend
`[ ]` not started · `[~]` in progress · `[x]` done · `[!]` blocked · `[-]` dropped/deferred

## Phase overview

| Phase | Name | Status | Notes |
|---|---|---|---|
| 0 | Foundation (repo, Django, DB, JWT, base React) | `[x]` | Done 2026-09-16. 38 tests green. |
| 1 | Accounts & Admin (users, roles, departments, audit, announcements) | `[x]` | Done 2026-09-16. 111 tests green. |
| 2 | Courses (structure, content, enrollment, assignments, progress) | `[ ]` | Next up |
| 3 | Exams (question bank, scheduling, attempts, grading, results) | `[ ]` | |
| 4 | Coding Portal (problems, test cases, Judge0, submissions) | `[ ]` | Needs Docker Desktop |
| 5 | Integration, notifications, reports, deploy, frontend upgrade | `[ ]` | |

---

## Completed

- 2026-09-16 — Read `LMS_Solution_Document.pdf`; wrote `Doc.md`, `rule.md`, `agent.md`, `CLAUDE.md`, `phases/PHASE-0..5`, `.gitignore`. Initial commit + push.
- 2026-09-16 — **Phase 0 done.** Backend: uv project, split settings, MySQL/MariaDB, custom `User` (email login, `role`), `Department`, JWT auth API (register, token, refresh, logout with blacklist, me, change-password), core permissions/pagination/error envelope, `seed_dev`, Swagger at `/api/docs/`. Frontend: Vite React TS with login, register, profile, role home stubs, route guards, axios token refresh. Verified: pytest 38 passed, ruff clean, OpenAPI schema valid, live smoke test (admin login → me → role=admin, CORS for localhost:5173), `npm run build` ok.
- 2026-09-16 — Fix: frontend login showed "Network error". Cause: another project (dsaclone) holds port 5173, so Vite moved to 5174, which CORS did not allow. Dev settings now allow any `localhost`/`127.0.0.1` port (prod unchanged); tests added. Frontend: show/hide password eye button on login and register; clearer message when API unreachable. Local test accounts live in gitignored `user.md`.
- 2026-09-16 — **Phase 1 done.**
  - `apps.audit`: `AuditLog`, `log_action()`, `AuditedModelMixin`, admin read-only `audit-logs/` with filters.
  - `apps.accounts`: `StudentProfile`/`FacultyProfile` (signal on save + data migration backfill), profile in `auth/me/` (bio editable), `departments/` (admin write, all read, user counts), admin `users/` (filters, search incl. roll/employee id, create with temp password, update with self-protection, deactivate with token revocation, reset-password, CSV bulk import with per-row errors).
  - `apps.notifications`: `Notification` + `notify()` (bulk insert, optional email), `notifications/` list/read/read-all/unread-count; `Announcement` with audiences all/faculty/students/department, visibility by role/department/publish window, delivery to audience on publish.
  - Frontend: admin Users (create/edit/reset/deactivate/bulk import), Departments, Audit log; Notifications with nav badge; Announcements list + post; forced Change password for temp passwords.
  - Verified: pytest 111 passed, ruff clean, OpenAPI schema with no warnings, `npm run build` ok, live API smoke test on local server (admin creates dept + faculty → faculty logs in with temp password → profile/department in `me` → notification received → faculty posts department announcement, blocked from posting to all → change password clears flag → deactivation rejects token). Smoke data deleted afterwards.

## In progress

- (none)

## Left / next actions

1. Start Phase 2: follow `phases/PHASE-2-courses.md`. Add `course` audience to announcements there.
2. Install Docker Desktop (WSL2 required on Windows Home) — needed by Phase 4, can be done any time.
3. Phase 5 hardening items found in Phase 1:
   - Enforce `must_change_password` in the API, not only the frontend.
   - Replace temporary passwords in API responses/emails with one-time set-password links.
   - Scheduler to deliver announcements whose `published_at` is in the future.
   - Invalidate access tokens on password reset (currently valid up to 30 min; refresh tokens are revoked).
4. Minor: oxlint warns `only-export-components` in `frontend/src/auth` (HMR only). Split hooks/helpers into own files when frontend grows.
5. Minor: git prints LF→CRLF warnings on every commit. Consider a `.gitattributes` with `* text=auto eol=lf`.

## Blocked

- (none)

---

## Decisions log

| Date | Decision | Why |
|---|---|---|
| 2026-09-16 | Backend = Django 5 + DRF; Frontend = React + TS + Vite | User choice; doc allows Django |
| 2026-09-16 | Auth = JWT via `djangorestframework-simplejwt` | Matches doc; stateless |
| 2026-09-16 | ~~DB = PostgreSQL 18~~ superseded | |
| 2026-09-16 | DB = MySQL via `mysqlclient`; local server on 3306 is MariaDB 12.3, db `forge_db`, user root (dev only) | User choice; doc lists MySQL as option |
| 2026-09-16 | Python deps via `uv` | Installed, fast, lockfile |
| 2026-09-16 | Monorepo `backend/` + `frontend/` | Solo dev, one history |
| 2026-09-16 | Code judge = Judge0 CE self-hosted via Docker Compose | Matches doc; sandboxed |
| 2026-09-16 | Redis/Celery deferred | YAGNI until bulk email / async grading needed |
| 2026-09-16 | File storage local `media/` in dev, `django-storages` later | Simple now, swappable |
| 2026-09-16 | Commits: Conventional Commits, no co-author trailers, push after every unit | User rule (`rule.md` §1) |
| 2026-09-16 | Frontend kept minimal until Phase 5 | User direction: backend is the main aim |
| 2026-09-16 | `user.md` (test credentials) gitignored | Repo is public; `rule.md` §1.6 forbids committing secrets |
| 2026-09-16 | Users are never hard-deleted via API; DELETE deactivates and revokes refresh tokens | Keeps audit history and submissions intact |
| 2026-09-16 | Admin-created users get a generated temporary password and `must_change_password` | No password travels from admin unless they choose one |
| 2026-09-16 | Faculty announcements limited to their own department | Plan said course/department scoped; course scope arrives with Phase 2 |

## Deviations from Doc.md / phase files

- Frontend scaffold is React 19 + react-router 7 + Vite 8 + TypeScript 6 (current Vite template), not React 18 as first written in `Doc.md`. Doc updated.
- Database is MySQL (MariaDB 12.3 locally) instead of PostgreSQL. Local dev uses `root` with empty password; never use outside dev.
- Phase 1 as-built notes are listed at the end of `phases/PHASE-1-accounts-admin.md`.

## Environment notes

- Machine: Windows 11 Home, PowerShell.
- Installed: Python 3.10.11, uv, Node 22.23.2, MariaDB 12.3 on port 3306 (service `MariaDB`), PostgreSQL 18 (unused), Git.
- Missing: Docker Desktop, Redis.
- Parent dir `d:\code\GITHUB\CLAUDE.md` belongs to a different project (Innolance LMS, Node/Express). Forge's own `CLAUDE.md` overrides it for this repo.
- Port 5173 is often taken by another local project (dsaclone); Forge's Vite then runs on 5174.

## Session log

| Date | Summary | Commits |
|---|---|---|
| 2026-09-16 | Project bootstrap: docs, rules, phases | `docs: bootstrap project docs and phase plans` |
| 2026-09-16 | Phase 0 foundation: backend auth + minimal frontend; switched DB to MySQL | `chore: scaffold django backend with uv`, `feat(accounts): custom user model, jwt auth endpoints, core utilities`, `chore(core): switch database to mysql (mariadb)`, `docs: record mysql decision and phase 0 backend progress`, `chore(frontend): vite react scaffold with jwt auth`, `docs: complete phase 0` |
| 2026-09-16 | Test accounts, CORS port fix, password eye button | `chore: gitignore local test account file`, `fix(core): allow any localhost port for cors in dev`, `feat(frontend): password visibility toggle and clearer api error` |
| 2026-09-16 | Phase 1 accounts & admin | `docs: start phase 1`, `feat(audit): audit log model, log_action service, admin api`, `feat(accounts): student/faculty profiles and department api`, `feat(notifications): in-portal notifications with email option`, `feat(accounts): admin user management api`, `feat(notifications): announcements with audience rules`, `feat(frontend): admin users, departments, audit log, notifications, announcements`, `docs: complete phase 1` |
