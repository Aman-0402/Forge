# Phase 5 — Integration, Reports, Hardening, Deployment, Frontend Upgrade

**Goal:** All three modules work together end to end; admin gets reports and analytics; email notifications go out; security and performance are hardened; the stack is deployable with Docker Compose; the frontend is upgraded from "minimal" to a proper responsive UI.

**Maps to source doc:** Week 4 (integration, UAT, deployment), §9 NFRs, §11 notification layer, deliverables §15.

**Depends on:** Phases 0–4.

**Estimated effort:** 4–5 days (frontend upgrade may extend).

## 5.1 Cross-module integration
- [ ] Course dashboard aggregates: lessons progress, assignments, exams, coding problems for that course in one endpoint `courses/{id}/dashboard/` (student view) and `courses/{id}/overview/` (faculty view with batch stats).
- [ ] Student home `me/dashboard/`: enrolled courses w/ progress, upcoming exams, pending assignments, recent coding verdicts, unread notifications.
- [ ] Faculty home `faculty/dashboard/`: my courses, pending grading counts (assignments + subjective answers), upcoming exams, recent submissions.
- [ ] Auto-enrollment signals verified across modules (new student in department → auto courses → eligible exams/problems).
- [ ] End-to-end scenario test (pytest, single test module) walking admin → faculty → student through all three modules.

## 5.2 Reports & analytics (admin)
- [x] `reports/overview/` (2026-09-17): users by role + active/inactive, courses by status, enrollments by status, top 8 courses by active enrollment, exam pass/fail/ungraded, coding submissions by verdict, problems by difficulty, contact message count. Frontend `/admin/analytics`: 6 stat tiles + 5 donut charts + 2 bar charts (recharts), verified in both light and dark theme against live seeded data. No CSV export, no judge-health check, no "this month/this week" time windows — plain running totals only.
- [ ] `reports/courses/`: enrollment counts, completion rates, avg progress per course; CSV export.
- [ ] `reports/exams/`: attempts, avg/median score, pass rate, integrity event counts per exam; CSV export.
- [ ] `reports/coding/`: problems solved, acceptance rate per problem, top students.
- [ ] `reports/students/{id}/`: one student full history (for faculty/admin).
- [ ] Query performance: annotate/aggregate in DB, add indexes found via `django-debug-toolbar` (dev only) or `EXPLAIN`.

## 5.3 Notifications & email
- [ ] Email templates (HTML + text) for: account created (set-password link), enrollment, exam scheduled, exam results released, assignment graded, announcement.
- [ ] SMTP settings from env; provider chosen with client (SMTP vs SES). Console backend stays in dev.
- [ ] Decide on async: if email volume warrants → add Celery + Redis (`infra/docker-compose.yml` services) and move `notify(email=True)` + Judge0 polling to tasks. Otherwise keep synchronous. Record decision in `agent.md`.
- [ ] Notification preferences on profile (email on/off per kind) — optional.

## 5.4 Security & hardening
- [x] `prod.py`: `DEBUG=False`, `SECURE_*` settings (HSTS, SSL redirect, secure cookies), `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` (both required env vars; `require_prod_settings` raises `ImproperlyConfigured` at startup if either is unset, instead of silently refusing every request).
- [ ] DRF throttling defaults: anon 30/min, user 300/min; login endpoint 10/min per IP.
- [x] Password validators, account lockout after N failed logins (simple cache counter: 5 fails lock the email 15 min).
- [x] Session revocation on password change/reset/deactivation (exact `sv` token claim) and `must_change_password` enforced in the API.
- [x] Scheduled announcements delivered exactly once: `delivered_at` + `deliver_scheduled_announcements` command (cron every minute); UI can schedule posts.
- [x] One-time set-password links replace temporary passwords (invite, admin reset, forgot password) + frontend `/set-password` and `/forgot-password`.
- [~] Upload hardening: size limits and random filenames done earlier. Private uploads (course content, assignment briefs, submissions) now download only through signed, expiring `/api/v1/files/` links; dev `/media/` serves avatars and thumbnails only; prod uses `PROTECTED_MEDIA_NGINX_PREFIX` + X-Accel-Redirect. Content-type sniffing still open.
- [ ] Judge0 not exposed publicly; backend-only network.
- [x] Dependency audit (2026-09-17): `pip-audit` on the backend and `npm audit` on the frontend — 0 known vulnerabilities on both. Re-run before deployment and periodically after.
- [ ] Run `/security-review` on the branch; fix findings.
- [x] Logging: `RequestIDMiddleware` stamps every request (and every log line it produces) with an id, echoed as `X-Request-ID`; console format in dev, JSON (`apps/core/logging.py`) in prod. Error tracking hook: set `SENTRY_DSN` + `uv sync --extra sentry`, optional.

## 5.5 Performance
- [ ] Load test exam attempt flow (e.g. `locust`) with 200 concurrent students on local Compose; target p95 answer-save < 300 ms.
- [ ] Add Redis cache (`django-redis`) if measured need: exam question payload cache, course tree cache, leaderboard.
- [ ] DB indexes review: `Attempt(exam, student)`, `Answer(attempt, exam_question)`, `Enrollment(course, student)`, `CodeSubmission(problem, student, submitted_at)`, `Notification(recipient, is_read)`.
- [ ] Pagination and `select_related`/`prefetch_related` audit on all list endpoints.

## 5.6 Deployment
- [ ] `backend/Dockerfile` (multi-stage, `uv`, gunicorn), `frontend/Dockerfile` (build → Nginx static).
- [ ] `infra/docker-compose.yml`: `mysql`, `backend`, `frontend` (Nginx, also reverse proxies `/api/` and `/media/`), `judge0` stack (or `include:` the Judge0 compose), optional `redis`, `celery`.
- [ ] `.env.production.example`. Secrets via env / provider secret store.
- [ ] Backups: `mysqldump` cron container or provider snapshots; `media/` to S3 via `django-storages` in prod; restore procedure documented and tested once.
- [ ] Cloud target chosen with client (AWS / Azure / GCP / single VPS). Provision, DNS, TLS (Caddy or Certbot).
- [ ] CI (GitHub Actions): on push → `ruff`, `pytest` (MySQL service), `npm run build`. On tag → build and push images.
- [ ] Runbook `infra/RUNBOOK.md`: deploy, rollback, migrate, backup/restore, rotate secrets, Judge0 restart.

## 5.7 Frontend upgrade
- [x] Public marketing site (2026-09-17): `/`, `/programs`, `/master-class`, `/how-we-work`, `/contact`, `/techies` are a literal copy of the sibling `dsaclone` project's pages (`frontend/src/marketing/`, dark glassmorphism theme, framer-motion, lucide-react, ogl). `/login` and `/register` reuse dsaclone's visuals, wired to the real API and the required `PasswordInput` eye-toggle. Scoped under `.marketing-site` so it can't affect the authenticated app's own steel design — see agent.md decisions log. The authenticated app keeps plain CSS, no Tailwind/component kit added.
- [ ] Add Tailwind CSS + a component kit (shadcn/ui or similar), `@tanstack/react-query` for server state, form library (`react-hook-form` + `zod`) — for the authenticated app only, still deferred.
- [ ] Responsive layout shell: sidebar + top bar, role-based nav, mobile drawer.
- [ ] Rebuild pages per role with proper UX: dashboards, course viewer (video player, PDF viewer), exam attempt screen (question palette, timer, full-screen mode, integrity prompts), coding page (Monaco, split panes, verdict panel), grading queues, reports with charts.
- [ ] Accessibility pass (keyboard nav, labels, contrast). Cross-browser check (Chrome, Edge, Firefox, Safari iOS).
- [ ] Generate TypeScript API client from `/api/schema/` (`openapi-typescript`) to keep types in sync.

## 5.8 UAT & handover
- [ ] Seed realistic demo data command `seed_demo`.
- [ ] Role walkthrough docs (`docs/user-guide/admin.md`, `faculty.md`, `student.md`) — deliverable in source doc.
- [ ] UAT checklist executed with client; bugs tracked in `agent.md` until closed.
- [ ] Tag `v1.0.0`. Update `agent.md` with post-launch support notes.

## Definition of done
- Full stack starts with one `docker compose up` locally and on the chosen cloud host.
- CI green on `main`. Backups verified by a restore.
- Admin dashboard reports populated from real activity.
- Frontend usable on phone, tablet, desktop for all three roles.
- Tagged `v1.0.0`, pushed.
