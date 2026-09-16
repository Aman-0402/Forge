# Forge LMS

This file overrides the parent-directory `CLAUDE.md` (which belongs to a different project). Everything below applies to `D:\code\GITHUB\Forge` only.

## Read first, every session
1. `rule.md` — working rules. Commit + push after every unit of work. **No co-author trailers.**
2. `agent.md` — current status. Update at start and end of work.
3. `Doc.md` — design, stack, data model, API surface.
4. `phases/PHASE-N-*.md` — the plan for the active phase.

## Stack
- Backend: Python 3.10+, Django 5, Django REST Framework, SimpleJWT, MySQL (local server is MariaDB 12.3, db `forge_db`), managed with `uv` (`backend/`).
- Frontend: React 19 + TypeScript + Vite, react-router-dom, axios (`frontend/`). Plain-CSS design system in `src/index.css` (tokens at top; content max width 1450px). No UI library until Phase 5.
- Code judge: Judge0 CE via Docker Compose (`infra/judge0/`).
- Shell: PowerShell on Windows 11.

## Commands
```powershell
# backend
cd backend
uv sync
uv run python manage.py migrate
uv run python manage.py seed_dev             # dev users
uv run python manage.py seed_demo_courses     # demo courses (after seed_dev)
uv run python manage.py seed_demo_exams       # demo bank + exams (after seed_demo_courses)
uv run python manage.py sweep_overdue_attempts # run every minute in production
uv run python manage.py deliver_scheduled_announcements # run every minute in production
uv run python manage.py seed_demo_problems    # languages + demo coding problems (after seed_demo_courses)
uv run python manage.py judge0_check          # live Judge0 smoke test (needs infra/judge0 running)

# judge0 (needs Docker Desktop; see infra/judge0/README.md)
cd infra\judge0; .\setup.ps1; docker compose up -d
uv run python manage.py runserver
uv run pytest
uv run ruff check . ; uv run ruff format .

# frontend
cd frontend
npm install
npm run dev
npm run build
```

## Conventions (short form — full list in rule.md)
- Custom user model `accounts.User` with `role ∈ {admin, faculty, student}`.
- Business logic in `services.py`; views thin; all API under `/api/v1/`; every list paginated.
- Permissions from `apps/core/permissions.py`.
- TDD: failing test → implement → green → commit.
- Migrations committed; never edit applied ones.
- Never serialize hidden test cases, correct answers pre-release, or password hashes.
