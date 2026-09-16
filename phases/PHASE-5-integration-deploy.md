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
- [ ] `reports/overview/`: users by role, active courses, exams this month, submissions this week, judge health.
- [ ] `reports/courses/`: enrollment counts, completion rates, avg progress per course; CSV export.
- [ ] `reports/exams/`: attempts, avg/median score, pass rate, integrity event counts per exam; CSV export.
- [ ] `reports/coding/`: problems solved, acceptance rate per problem, top students.
- [ ] `reports/students/{id}/`: one student full history (for faculty/admin).
- [ ] Query performance: annotate/aggregate in DB, add indexes found via `django-debug-toolbar` (dev only) or `EXPLAIN`.

## 5.3 Notifications & email
- [ ] Email templates (HTML + text) for: account created (temp password), enrollment, exam scheduled, exam results released, assignment graded, announcement.
- [ ] SMTP settings from env; provider chosen with client (SMTP vs SES). Console backend stays in dev.
- [ ] Decide on async: if email volume warrants → add Celery + Redis (`infra/docker-compose.yml` services) and move `notify(email=True)` + Judge0 polling to tasks. Otherwise keep synchronous. Record decision in `agent.md`.
- [ ] Notification preferences on profile (email on/off per kind) — optional.

## 5.4 Security & hardening
- [ ] `prod.py`: `DEBUG=False`, `SECURE_*` settings (HSTS, SSL redirect, secure cookies), `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`.
- [ ] DRF throttling defaults: anon 30/min, user 300/min; login endpoint 10/min per IP.
- [ ] Password validators, account lockout after N failed logins (`django-axes` or simple counter) — optional.
- [ ] Upload hardening: content-type sniff, size limits, filenames randomized, `media/` served by Nginx.
- [ ] Judge0 not exposed publicly; backend-only network.
- [ ] Dependency audit: `uv pip audit` / `npm audit`.
- [ ] Run `/security-review` on the branch; fix findings.
- [ ] Logging: structured JSON logs in prod, request id middleware, error tracking hook (Sentry DSN optional).

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
- [ ] Add Tailwind CSS + a component kit (shadcn/ui or similar), `@tanstack/react-query` for server state, form library (`react-hook-form` + `zod`).
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
