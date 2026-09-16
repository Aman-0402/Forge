# Strix security test report — Forge LMS

| Item | Value |
|---|---|
| Tool | [Strix](https://github.com/usestrix/strix) 1.6.2 (AI penetration testing agents) |
| Installed | 2026-09-17 with `uv tool install strix-agent` → `C:\Users\AMAN0402\.local\bin\strix.exe` |
| Commit under test | `bf892ec` (main) |
| Status | **Not run — blocked** |

## Result

No scan has run yet, so this report contains **no Strix findings**. Two prerequisites are missing on this machine:

1. **Docker.** Strix runs every agent inside a Docker sandbox. The first attempt stopped immediately:
   ```
   strix -n --target http://localhost:8000
   DOCKER NOT INSTALLED — The 'docker' CLI was not found in your PATH.
   ```
   Docker Desktop and WSL2 are also what Phase 4 (Judge0) is waiting for. See `infra/judge0/README.md`.
2. **LLM API key.** Strix drives its agents with an LLM. None of `LLM_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` or `OPENROUTER_API_KEY` is set. A deep scan can cost several dollars; use `--max-budget`.

## How to run once unblocked

Run from the repo root in PowerShell. Keep the dev servers running: backend on 8000, Vite on 5174.

```powershell
# 1. One-time: key and model (session only; never commit keys)
$env:STRIX_LLM   = "anthropic/claude-sonnet-5"
$env:LLM_API_KEY = "<your key>"

# 2. Local test accounts: copy the scan brief and add passwords from user.md (gitignored copy)
Copy-Item docs\security\strix-instructions.md strix-instructions.local.md
#    edit strix-instructions.local.md → fill in the passwords

# 3. Quick smoke scan of the running API (containers reach the host via host.docker.internal)
strix -n -m quick --max-budget 5 `
  --target http://host.docker.internal:8000 `
  --target http://host.docker.internal:5174 `
  --instruction-file strix-instructions.local.md

# 4. Full scan: live app + source code + OpenAPI spec
cd backend; uv run python manage.py spectacular --file ..\openapi.yaml; cd ..
strix -n -m deep --max-budget 25 `
  --target http://host.docker.internal:8000 `
  --target .\backend `
  --target .\openapi.yaml `
  --instruction-file strix-instructions.local.md
```

Notes:
- Strix mounts local directory targets **writable** inside the sandbox. Commit or stash work first, then check `git status` after the scan.
- Results land in `strix_runs/<run-name>/` (gitignored). Open them with `strix view`.
- Use a throwaway database or re-run `seed_dev` afterwards, because agents create users, courses and submissions.
- Django `DEBUG=True` in dev may show findings that do not apply in production (`config/settings/prod.py`). Tag those in the table below.

## Scope

In scope: the Django API (`/api/v1/`, `/api/schema/`, `/admin/`), the React app, and the backend source. Out of scope: Judge0 (not running) and third-party services.

Areas to stress, based on what Phase 5 just changed:
- Authentication: lockout, token refresh and revocation, forced password change, one-time set-password and forgot-password links.
- Access control and IDOR across roles: courses, enrollments, submissions, exam attempts and results, code submissions, admin user management.
- Signed file links under `/api/v1/files/`: forgery, replay after expiry, path traversal, and public `/media/` exposure.
- Exam integrity: submitting after the deadline, answering other students' attempts, reading answers before results are released.
- Code runner: source size limits, throttles, and hidden test-case leakage.
- Uploads: extension and size checks, content sniffing (known gap), XSS via file names or rich text.

## Findings

| # | Severity | Title | Endpoint / file | Applies to prod? | Status |
|---|---|---|---|---|---|
| — | — | Scan not run yet | — | — | — |

Fill this table from `strix_runs/<run>/` and track each open item in `agent.md` until fixed. Every fix needs a regression test, following `rule.md`.

## Security controls already covered by automated tests

These are not Strix results. They are behaviours the pytest suite checks on every run: 330+ tests at commit `bf892ec`.
- Role permissions on every module, with 404 rather than 403 for other staff's drafts.
- JWT revocation after password change, reset or deactivation, including tokens issued in the same second.
- Login lockout after 5 failures per email, and scoped throttles on auth, code run and code submit.
- One-time set-password links that fail on reuse, tampering or a weak password. Forgot-password returns 204 for every email.
- Signed file links reject tampered, re-pointed and expired tokens. Private folders are not served from `/media/`.
- Server-side exam timing, and hidden test cases redacted for students.
