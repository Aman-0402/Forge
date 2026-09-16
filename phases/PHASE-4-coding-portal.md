# Phase 4 — Coding Portal

**Goal:** Faculty create programming problems with visible and hidden test cases; students write code in a browser editor, run it against sample cases, and submit for automated evaluation against all cases in a sandboxed Judge0 instance; full submission history; optional leaderboard.

**Maps to source doc:** §8 Module 3, Weeks 3–4.

**Depends on:** Phase 1 (users), Phase 2 optional (problem may belong to a course). **Docker Desktop must be installed.**

**Estimated effort:** 4 days.

## Infra: Judge0 CE

- [ ] Install Docker Desktop (WSL2 backend). Verify `docker run hello-world`.
- [ ] `infra/judge0/`: download official Judge0 CE release bundle (`docker-compose.yml` + `judge0.conf`). Set a random `REDIS_PASSWORD`, `POSTGRES_PASSWORD`. Expose API on `localhost:2358` only.
- [ ] `docker compose up -d` in `infra/judge0/`; verify `GET http://localhost:2358/languages` and a sample Python submission.
- [ ] Add `JUDGE0_URL`, `JUDGE0_AUTH_TOKEN` (optional), `JUDGE0_TIMEOUT_SECONDS` to backend `.env.example`.
- [ ] `infra/judge0/README.md` with start/stop and Windows notes (WSL2, cgroup v1 requirement: Judge0 needs `systemd.unified_cgroup_hierarchy=0` in `%UserProfile%\.wslconfig` kernel command line; document exact steps).

## Data model (`apps/coding`)

| Model | Fields |
|---|---|
| `Language` | `name`, `judge0_id` (int, unique), `slug`, `version`, `is_enabled`, `default_template` (text), `order` |
| `Problem` | `title`, `slug` (unique), `statement` (markdown), `input_format`, `output_format`, `constraints`, `difficulty` (enum easy/medium/hard), `tags` JSON, `time_limit_seconds` (float, default 2), `memory_limit_kb` (int, default 128000), `max_score` (int, default 100), `course` FK null, `created_by` FK, `status` (enum draft/published/archived), `allowed_languages` M2M Language (empty = all enabled), `visible_from`, `visible_until` (null = always), timestamps |
| `TestCase` | `problem` FK, `input` (text), `expected_output` (text), `is_hidden` (bool), `is_sample` (shown in statement), `weight` (int, default 1), `order`, `explanation` (for samples) |
| `CodeSubmission` | `problem` FK, `student` FK, `language` FK, `source_code` (text), `kind` (enum run/submit), `status` (enum queued/running/done/error), `verdict` (enum accepted/wrong_answer/tle/mle/runtime_error/compile_error/partial/internal_error, null), `score` (int), `passed_count`, `total_count`, `max_time_seconds`, `max_memory_kb`, `compile_output`, `submitted_at`, `judged_at` |
| `TestCaseResult` | `submission` FK, `test_case` FK, `judge0_token` (char), `status` (enum from Judge0 status ids mapped), `stdout` (truncated), `stderr` (truncated), `time_seconds`, `memory_kb`, `passed` |
| `LeaderboardEntry` (optional) | `problem` FK null (null = global), `student` FK, `best_score`, `solved_count`, `last_solved_at` — recomputed on accepted submission |

## Judge0 client (`apps/coding/judge0.py`)
- `httpx.Client` with base URL, timeout, optional auth header.
- `create_batch(submissions: list[dict]) -> list[token]` using `POST /submissions/batch?base64_encoded=true` with `source_code`, `language_id`, `stdin`, `expected_output`, `cpu_time_limit`, `memory_limit`.
- `get_batch(tokens) -> list[result]` using `GET /submissions/batch?tokens=...&base64_encoded=true&fields=...`.
- Start with **`wait=true` on single-submission path for `run`** (sample cases only, ≤3) and **batch + short polling loop for `submit`** (poll every 0.5 s up to `JUDGE0_TIMEOUT_SECONDS`, executed inline in request). Documented upgrade path: move polling to Celery task + WebSocket/poll endpoint once latency or throughput demands.
- Map Judge0 `status.id` → our verdict (3 = Accepted, 4 = Wrong Answer, 5 = TLE, 6 = Compilation Error, 7–12 = Runtime Error, 13 = Internal Error, 14 = Exec Format Error).
- Compare output with trailing-whitespace normalization (Judge0 does when `expected_output` given; keep our own fallback compare).

## Business rules (services.py)
- **Run** (`kind=run`): executes against `is_sample=True` cases only (or custom stdin supplied by student → single execution, no verdict). Not stored in history if `store_runs=False` setting; default store last 10 per student per problem.
- **Submit** (`kind=submit`): executes against **all** test cases. `score = max_score * passed_weight / total_weight`. Verdict = `accepted` if all pass; `partial` if some pass (and problem allows partial, default true); else the first failing verdict by order.
- Students never receive hidden test case `input`/`expected_output`/`stdout`; only `passed`, `time`, `memory` per hidden case. Sample cases return full detail.
- Rate limit: `run` 10/min, `submit` 5/min per student (DRF throttling scopes).
- Source size limit 64 KB. Language must be in `allowed_languages` (or enabled if empty).
- Problem visible to students only when `published` and within visibility window and (if course-bound) enrolled.
- Faculty can edit problems they created; admin any. Editing test cases after submissions exist is allowed but logged; optional `rejudge` action re-runs all submissions.
- Leaderboard (optional): per problem ordered by `best_score desc, last_solved_at asc`; global by `solved_count`.

## API

| Method | Path | Role |
|---|---|---|
| GET | `languages/` | any |
| POST | `languages/sync/` | admin — pull from Judge0 `/languages`, upsert |
| CRUD | `problems/` · `problems/{id}/` | faculty/admin write; students see published |
| POST | `problems/{id}/publish/` · `archive/` · `rejudge/` | owner / admin |
| CRUD | `problems/{id}/testcases/` · `testcases/{id}/` | owner / admin only (students never list this endpoint) |
| POST | `problems/{id}/testcases/import/` | JSON/zip of `NN.in`/`NN.out` pairs |
| POST | `problems/{id}/run/` `{language, source_code, stdin?}` | student / faculty (faculty can test before publish) |
| POST | `problems/{id}/submit/` | eligible student |
| GET | `problems/{id}/submissions/` | own student; faculty/admin all with `?student=` |
| GET | `submissions/{id}/` | own student (hidden case detail redacted) / faculty / admin |
| GET | `me/coding/summary/` | student — solved counts, recent |
| GET | `problems/{id}/leaderboard/` · `leaderboard/` | any (optional) |

## Checklist
- [ ] Docker Desktop + Judge0 up; README written.
- [ ] Models, migrations, factories; `Language` seed via `languages/sync/` or fixture with Python/C/C++/Java/JS ids.
- [ ] Judge0 client with unit tests using `httpx.MockTransport` (no live Judge0 in unit tests); one marked `integration` test hitting real Judge0 (skipped if unreachable).
- [ ] Problem + test case CRUD, visibility rules, serializer redaction tests (assert hidden fields absent for student).
- [ ] Run endpoint + throttling + tests.
- [ ] Submit endpoint: batch create → poll → aggregate → verdict/score; tests with mocked transport covering accepted / wrong answer / TLE / compile error / partial.
- [ ] Submission history + detail redaction + tests.
- [ ] Rejudge action + audit.
- [ ] Optional: leaderboard recompute on accepted submission + endpoint.
- [ ] Notifications: new problem published in enrolled course. Audit: publish, submit, rejudge.
- [ ] Frontend (minimal): problem list, problem page with `@monaco-editor/react` (this one dependency is worth adding now), language select, Run (shows sample results) and Submit (shows per-case pass/fail + verdict), submissions history; faculty problem editor with test case table.
- [ ] Update `agent.md`; commit + push per feature.

## Definition of done
- Faculty creates "Sum of two numbers" with 2 sample + 3 hidden cases, publishes.
- Student runs Python solution → sample results shown; submits → `accepted`, score 100; submits wrong solution → `wrong_answer`, partial score; hidden inputs not in response body.
- Submission history lists both. Tests green, pushed.
