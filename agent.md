# Forge LMS — Agent Work Tracker

> Single source of truth for project status. Update at start and end of every work session (see `rule.md` §2).
> Design: `Doc.md`. Rules: `rule.md`. Phase plans: `phases/`.

**Last updated:** 2026-09-16
**Current phase:** Phase 4 — Coding Portal (code complete; live Judge0 verification waiting on Docker Desktop). Phases 0–3 done. Phase 5 can start in parallel.
**Repo:** https://github.com/Aman-0402/Forge.git (branch `main`)

---

## Status legend
`[ ]` not started · `[~]` in progress · `[x]` done · `[!]` blocked · `[-]` dropped/deferred

## Phase overview

| Phase | Name | Status | Notes |
|---|---|---|---|
| 0 | Foundation (repo, Django, DB, JWT, base React) | `[x]` | Done 2026-09-16. 38 tests green. |
| 1 | Accounts & Admin (users, roles, departments, audit, announcements) | `[x]` | Done 2026-09-16. 111 tests green. |
| 2 | Courses (structure, content, enrollment, assignments, progress) | `[x]` | Done 2026-09-16. 203 tests green. Certificates deferred to Phase 5. |
| 3 | Exams (question bank, scheduling, attempts, grading, results) | `[x]` | Done 2026-09-16. 272 tests green. |
| 4 | Coding Portal (problems, test cases, Judge0, submissions) | `[~]` | Code complete 2026-09-16, 317 tests green (1 live Judge0 test skipped). Live verification blocked on Docker Desktop. |
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

- 2026-09-16 — **Phase 2 done.**
  - `apps.courses`: categories; courses with role-based visibility, instructor/co-instructors, approval flow (submit, approve, reject with reason, archive), delete only empty drafts.
  - Structure: modules → chapters → lessons → content (video/pdf/ppt/doc/link/text) with nested CRUD, reorder, upload validation by kind and size, preview lessons, one-call course tree with locked content and completion flags.
  - Enrollment: open self-enroll/drop, manager bulk add by ids/batch/department, roster and removal, my enrollments, automatic enrollment by department or batch (on publish, on user/profile change, `sync_auto_enrollments` command; dropped students are not re-added).
  - Progress: complete lesson, video position, percent recompute on lesson add/remove, completion notification, manager progress table.
  - Assignments: attachments, due dates, late rules, submit/resubmit until graded, grading with notification.
  - Announcements gained a `course` audience.
  - `seed_demo_courses` command for local demo data (run on local DB).
  - Frontend redesign on user request ("basic UI, good CSS", "content area 1450px"): plain-CSS design system (steel palette, Archivo + IBM Plex, sidebar shell, temper-gradient progress bars), new login/register frame, course catalog, course form, course page (content viewer, assignments, students, manage + structure editor), assignment submit/grading, my learning, role home pages, admin approvals and categories.
  - Verified: pytest 203 passed, ruff clean, OpenAPI schema clean, `npm run build` ok, Playwright screenshots via Edge at 1600px and 400px with no console errors, live API smoke of the phase definition of done (faculty builds course + PDF → submit → admin approve → student enroll → 100% completed → assignment submit → graded → notifications → PDF served). Smoke data deleted afterwards.

- 2026-09-16 — **Phase 3 done.**
  - `apps.exams` models: question banks, questions + options, exams, exam questions, attempts, answers, integrity events.
  - Banks: ownership and sharing, option rules per type, JSON import (all-or-nothing), questions locked once attempted, delete protection.
  - Exam builder: course-owned exams, eligibility (allowed list → course enrollment → everyone), add by id or random pick, marks override, schedule/unschedule/extend/close, edits locked after first attempt, scheduling notifies eligible students.
  - Attempts: start/resume with persisted question and option order, answers saved until deadline + 10 s grace, submit with objective grading (negative marks, exact-set multi), totals and pass flag, lazy auto-submit, close auto-submits, `sweep_overdue_attempts` command, integrity events. Correct answers never sent before release.
  - Grading and results: attempt list with integrity counts, full review, written-answer grading and regrade, release (blocked while grading pending) with notifications, student scorecard with optional answer reveal, results stats + CSV export, my results.
  - `seed_demo_exams` and `exam_load_check` commands.
  - Frontend: question banks + question editor + JSON import, exams list, exam form, staff exam page (publishing, questions, attempts, results + CSV), student exam page, distraction-free exam screen (server-synced timer, autosave, palette, auto-submit, full screen, integrity events), scorecard, review + grading, my results.
  - Verified: pytest 272 passed, ruff clean, OpenAPI schema clean, `npm run build` ok, load check (200 students x 10 questions, 50 workers: 3980 answer saves, 199 submits, 0 application errors, 0 duplicate attempts; 1 connection refused by runserver), Playwright screenshots of student and staff exam flows with no console errors. Screenshot and load-test data deleted afterwards.

- 2026-09-16 — **Phase 4 code complete (live Judge0 not yet verified).**
  - `infra/judge0/`: compose file from the Judge0 CE 1.13.1 release (API bound to 127.0.0.1), config template, `setup.ps1` that writes random secrets into gitignored `judge0.conf`, README covering WSL2, Docker Desktop and cgroup v1.
  - `apps.coding`: languages (`seed_languages` with Judge0 ids), problems (course ownership, visibility window, allowed languages, publish/unpublish/archive, course notification on publish), test cases (sample vs hidden, weights, JSON import).
  - Judge0 client (httpx): base64 payloads, auth token, 20-item batches, polling with timeout, clear unreachable/auth errors. Tests run against an in-memory fake Judge0.
  - Judging: run against samples or custom input (not stored); submit against all cases with per-case verdicts, weighted partial score, whitespace-tolerant comparison; hidden cases redacted for students; language and 64 KB source limits; throttles 10 runs/min and 5 submits/min; 503 with recorded error when Judge0 is down; rejudge; leaderboard; my coding summary; `judge0_check` and `seed_demo_problems` commands.
  - Frontend: problems list, problem form, split workspace (statement, Monaco editor bundled locally with per-language drafts, run/submit output), submissions, leaderboard, staff test-case editor and rejudge, submission detail. DOMPurify pinned via npm overrides (npm audit clean).
  - Verified: pytest 317 passed + 1 live test skipped, ruff clean, OpenAPI schema clean, `npm run build` ok, Playwright screenshots (student workspace, staff test cases, mobile) with no console errors; "runner unavailable" message confirmed in the UI.

## In progress

- Phase 4 live verification — waiting for Docker Desktop (see Blocked and `phases/PHASE-4-coding-portal.md` "Still to verify").
## Left / next actions

1. Install Docker Desktop (WSL2 required on Windows Home) — needed by Phase 4, can be done any time.
2. Phase 5 hardening items found in Phase 1:
   - Enforce `must_change_password` in the API, not only the frontend.
   - Replace temporary passwords in API responses/emails with one-time set-password links.
   - Scheduler to deliver announcements whose `published_at` is in the future.
   - Invalidate access tokens on password reset (currently valid up to 30 min; refresh tokens are revoked).
   - Serve course media and submissions through access checks (currently public `/media/` URLs with random names).
   - Course completion certificates (deferred from Phase 2).
3. Phase 5 items found in Phase 3:
   - Schedule `sweep_overdue_attempts` every minute.
   - Measure exam answer-save latency under gunicorn (target p95 < 300 ms); dev runserver gave 1.3 s at 50 concurrent workers.
   - Confirm integrity-event policy with the client (currently record-only).
   - Optional: partial credit for multi-answer questions, CSV question import.
4. Phase 5 items found in Phase 4:
   - Move judging off the request thread (task queue) if submit latency or volume grows.
   - Run Judge0 on a dedicated host/network in production (containers are privileged).
   - Watch for a transient Windows pytest temp-dir error seen once in Phase 4 (rerun passed).
5. Minor: oxlint `only-export-components` warnings for small helpers exported next to components (HMR only).

## Blocked

- Live Judge0 execution: Docker Desktop and WSL2 are not installed on this machine (checked 2026-09-16). Needs admin rights and a reboot by the user. All Phase 4 code is built and tested against a fake Judge0; follow `infra/judge0/README.md`, then the "Still to verify" list in `phases/PHASE-4-coding-portal.md`.

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
| 2026-09-16 | Faculty may also post announcements to courses they teach | Phase 2 course audience |
| 2026-09-16 | Frontend gets a real visual design now (plain CSS, no UI library), content max width 1450px | User request during Phase 2 |
| 2026-09-16 | `.gitattributes` normalizes line endings to LF | Stops CRLF warnings on Windows |
| 2026-09-16 | Exam live/ended state derived from the time window, not stored | No scheduler needed to flip statuses |
| 2026-09-16 | Exam timing server-authoritative with 10 s grace; overdue attempts submitted lazily plus sweep command | Correctness without relying on client clocks |
| 2026-09-16 | Exam screen renders outside the sidebar layout | Distraction-free test taking |
| 2026-09-16 | Build Phase 4 against a fake Judge0 while Docker is missing | Keeps momentum; live checks listed for later |
| 2026-09-16 | Judge synchronously in the submit request; backend compares output itself | Simplest correct design; independent of Judge0 comparison rules |
| 2026-09-16 | Monaco bundled locally, lazy-loaded; DOMPurify pinned via npm overrides | No CDN dependency; clears npm audit |
| 2026-09-16 | Commit commands gated on lint passing | Two lint slips reached commits in Phases 2-4 |

## Deviations from Doc.md / phase files

- Frontend scaffold is React 19 + react-router 7 + Vite 8 + TypeScript 6 (current Vite template), not React 18 as first written in `Doc.md`. Doc updated.
- Database is MySQL (MariaDB 12.3 locally) instead of PostgreSQL. Local dev uses `root` with empty password; never use outside dev.
- Phase 1 as-built notes are listed at the end of `phases/PHASE-1-accounts-admin.md`.
- Phase 4 as-built notes are listed at the end of `phases/PHASE-4-coding-portal.md` (runs not stored, synchronous judging, no languages/sync endpoint).
- Phase 3 as-built notes are listed at the end of `phases/PHASE-3-exams.md` (derived exam phase instead of stored "live", JSON-only import, no partial credit).
- Phase 2 as-built notes are listed at the end of `phases/PHASE-2-courses.md`. Frontend is no longer "minimal" as `rule.md` §5 first said; user asked for a styled UI.

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
| 2026-09-16 | Phase 2 courses + frontend design system | `docs: start phase 2`, `feat(courses): course catalog, categories and approval flow`, `chore: normalize line endings with gitattributes`, `feat(courses): modules, chapters, lessons, content and course tree`, `feat(courses): enrollment (self, bulk, automatic rules)`, `feat(courses): lesson completion and course progress`, `feat(courses): assignments, submissions and grading`, `feat(notifications): course audience for announcements`, `chore(courses): seed_demo_courses command for local demo data`, `feat(frontend): course pages and steel design system`, `style(courses): fix line length in demo seed`, `style(frontend): temper gradient fill, full-height sidebar, mobile menu contrast`, `docs: complete phase 2` |
| 2026-09-16 | Phase 3 exams | `docs: start phase 3`, `docs: mark phase 3 in progress`, `feat(exams): question banks, questions and JSON import`, `feat(exams): exam builder, eligibility and scheduling`, `feat(exams): attempts with server timer and auto-grading`, `feat(exams): grading queue, result release and reports`, `chore(exams): exam_load_check command for concurrency testing`, `chore(exams): seed_demo_exams command for local demo data`, `feat(frontend): question banks, exams, exam taking and results`, `style(exams): fix line length in demo exam seed`, `feat(frontend): explain exam publishing state`, `docs: complete phase 3` |
| 2026-09-16 | Phase 4 coding portal (code complete) | `docs: start phase 4`, `chore(infra): judge0 docker compose, config template and setup`, `feat(coding): languages, problems and test cases`, `feat(coding): judge0 client with batching and polling`, `feat(coding): run, submit, verdicts, history and leaderboard`, `style(coding): fix line length in judge0_check`, `feat(frontend): coding portal with code editor`, `chore(coding): seed_demo_problems command for local demo data`, `feat(coding): notify enrolled students when a course problem is published`, `docs: phase 4 code complete` |
