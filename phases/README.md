# Phases

Backend-first build order. Each file has data model, business rules, API, checklist, and definition of done. Tick checklists here; mirror status in `../agent.md`.

| # | File | Focus | Est. |
|---|---|---|---|
| 0 | [PHASE-0-foundation.md](PHASE-0-foundation.md) | Django + DRF + JWT + custom User, Postgres, OpenAPI, minimal React login | 1–2 d |
| 1 | [PHASE-1-accounts-admin.md](PHASE-1-accounts-admin.md) | Admin user/department CRUD, profiles, audit log, notifications, announcements | 2 d |
| 2 | [PHASE-2-courses.md](PHASE-2-courses.md) | Course structure, content upload, enrollment, assignments, progress | 3–4 d |
| 3 | [PHASE-3-exams.md](PHASE-3-exams.md) | Question banks, scheduling, attempts, timer, auto/manual grading, results | 4 d |
| 4 | [PHASE-4-coding-portal.md](PHASE-4-coding-portal.md) | Judge0 via Docker, problems, test cases, run/submit, history | 4 d |
| 5 | [PHASE-5-integration-deploy.md](PHASE-5-integration-deploy.md) | Dashboards, reports, email, hardening, Docker Compose deploy, CI, frontend upgrade | 4–5 d |

Rules: do not start Phase N+1 "must" items while Phase N is open unless `agent.md` says why. Frontend stays minimal until Phase 5.7.
