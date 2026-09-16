# Forge LMS — Agent Work Tracker

> Single source of truth for project status. Update at start and end of every work session (see `rule.md` §2).
> Design: `Doc.md`. Rules: `rule.md`. Phase plans: `phases/`.

**Last updated:** 2026-09-16
**Current phase:** Phase 0 — Foundation (not started)
**Repo:** https://github.com/Aman-0402/Forge.git (branch `main`)

---

## Status legend
`[ ]` not started · `[~]` in progress · `[x]` done · `[!]` blocked · `[-]` dropped/deferred

## Phase overview

| Phase | Name | Status | Notes |
|---|---|---|---|
| 0 | Foundation (repo, Django, DB, JWT, base React) | `[ ]` | Next up |
| 1 | Accounts & Admin (users, roles, departments, audit, announcements) | `[ ]` | |
| 2 | Courses (structure, content, enrollment, assignments, progress) | `[ ]` | |
| 3 | Exams (question bank, scheduling, attempts, grading, results) | `[ ]` | |
| 4 | Coding Portal (problems, test cases, Judge0, submissions) | `[ ]` | Needs Docker Desktop |
| 5 | Integration, notifications, reports, deploy, frontend upgrade | `[ ]` | |

---

## Completed

- 2026-09-16 — Read `LMS_Solution_Document.pdf`; wrote `Doc.md`, `rule.md`, `agent.md`, `CLAUDE.md`, `phases/PHASE-0..5`, `.gitignore`. Initial commit + push.

## In progress

- (none)

## Left / next actions

1. Install Docker Desktop (WSL2 required on Windows Home) — needed by Phase 4, can be done any time.
2. Start Phase 0: follow `phases/PHASE-0-foundation.md`.

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

## Deviations from Doc.md / phase files

- (none)

## Environment notes

- Machine: Windows 11 Home, PowerShell.
- Installed: Python 3.10.11, uv, Node 22.23.2, MariaDB 12.3 on port 3306 (service `MariaDB`), PostgreSQL 18 (unused), Git.
- Missing: Docker Desktop, Redis.
- Parent dir `d:\code\GITHUB\CLAUDE.md` belongs to a different project (Innolance LMS, Node/Express). Forge's own `CLAUDE.md` overrides it for this repo.

## Session log

| Date | Summary | Commits |
|---|---|---|
| 2026-09-16 | Project bootstrap: docs, rules, phases | `docs: bootstrap project docs and phase plans` |
