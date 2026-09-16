# Forge LMS — Working Rules

These rules apply to every session, every agent, every commit. Read `agent.md` for current status and `Doc.md` for design.

## 1. Git — commit and push on every unit of work

1. **Every build step or update must be committed AND pushed** to `origin main` before the session ends or before moving to the next task. No local-only work left behind.
2. **No co-author lines.** Commit messages must NOT contain `Co-Authored-By:` or any AI attribution trailer. Plain author only (git user `Aman`).
3. **Conventional Commits** format, subject ≤ 50 chars, imperative mood:
   - `feat(exams): add attempt auto-submit sweep`
   - `fix(accounts): reject inactive users at login`
   - `docs: update agent.md after phase 1`
   - `chore: add ruff config`
   - `test(courses): cover enrollment permissions`
   Scopes = app names (`accounts`, `courses`, `exams`, `coding`, `notifications`, `audit`, `core`, `frontend`, `infra`, `docs`).
4. Body only when the "why" is not obvious from the subject.
5. Commit small and often. One logical change per commit. Never mix a feature with unrelated refactors.
6. Never commit: `.env`, `media/`, `node_modules/`, `.venv/`, `__pycache__/`, DB dumps, secrets of any kind. `.env.example` IS committed.
7. Never force-push `main`. Never rewrite pushed history.
8. Before pushing: `npm run check`/`ruff check` + tests must pass for the touched app. If tests fail, fix or commit as `wip:` with a clear note in `agent.md` — but still push.
9. Work directly on `main` for now (solo dev). Feature branches optional for risky experiments; merge with fast-forward or squash.

## 2. Tracking — `agent.md` is the single source of truth for status

1. Update `agent.md` at the **start** of work (mark task In Progress) and at the **end** (mark Done / Blocked / Left).
2. Every session ends with a `docs: update agent.md` commit if anything changed.
3. Record: what was completed, what is in progress, what is left, blockers, decisions made, and any deviation from `Doc.md` or the phase file.
4. If a decision changes design, update `Doc.md` in the same commit.

## 3. Phase discipline

1. Work follows `phases/PHASE-N-*.md` in order. Do not start Phase N+1 tasks while Phase N has open "must" items, unless `agent.md` records why.
2. Each phase file has a checklist. Tick items there AND reflect status in `agent.md`.
3. Backend first. Frontend in early phases is minimal: enough to exercise and demo the API. No design polish until Phase 5+.

## 4. Backend conventions (Django / DRF)

1. Python managed by **uv**. Run everything via `uv run` (`uv run python manage.py ...`, `uv run pytest`).
2. Settings split: `config/settings/base.py`, `dev.py`, `prod.py`. Secrets and DB URL from `.env` via `django-environ`.
3. Custom user model `accounts.User` with `role` field. Never use `django.contrib.auth.models.User` directly; use `get_user_model()` or `settings.AUTH_USER_MODEL`.
4. Every app: `models.py`, `serializers.py`, `views.py`, `urls.py`, `permissions.py` (if any), `services.py` (business logic), `tests/`.
5. Business logic lives in `services.py`, not in views or serializers.
6. All API under `/api/v1/`. ViewSets + DRF routers. Pagination on every list.
7. Permission classes from `apps/core/permissions.py`: `IsAdmin`, `IsFaculty`, `IsStudent`, `IsAdminOrFaculty`, `IsOwnerOrAdmin`. Default permission = `IsAuthenticated`.
8. Migrations are generated with `makemigrations` and **committed**. Never edit an applied migration; add a new one.
9. Tests: `pytest` + `pytest-django`. Write the failing test first (TDD), then implement. Minimum per endpoint: happy path, wrong role → 403, unauthenticated → 401.
10. `ruff check` and `ruff format` clean before commit.
11. Log significant writes via `apps.audit.services.log_action()`.
12. Never expose hidden test cases, correct answers (before result release), or password hashes in any serializer.

## 5. Frontend conventions (React / Vite)

1. TypeScript. `src/api/` holds axios client + typed calls. Token in memory + refresh token in `localStorage` (revisit at hardening).
2. Routing with `react-router-dom`. One page per backend feature, minimal styling.
3. `credentials` not needed (JWT header), but always send `Authorization: Bearer`.
4. No UI library until Phase 5. Plain CSS or none.

## 6. Security baseline

1. `DEBUG=False`, strong `SECRET_KEY`, `ALLOWED_HOSTS` set in prod.
2. Passwords via Django hashers only. Minimum length validators on.
3. JWT access lifetime ≤ 30 min, refresh ≤ 7 days, rotate refresh tokens, blacklist on logout.
4. CORS restricted to frontend origin.
5. File uploads: validate extension + size; serve `media/` via web server in prod, never via Django.
6. Judge0 reachable only from backend network, never from browser.

## 7. Communication

1. Chat responses stay terse (caveman mode active). Code, commits, docs written normal.
2. When blocked on a decision only the user can make, ask. Otherwise choose the sensible default, note it in `agent.md`, continue.
