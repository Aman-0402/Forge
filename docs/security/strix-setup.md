# Strix setup — unblock steps

Strix 1.6.2 is installed (`uv tool install strix-agent` → `strix.exe` on PATH). Two things
are still missing on this machine before a scan can run: Docker and an LLM API key.

## 1. Install WSL2

In an **admin** PowerShell:

```powershell
wsl --install
```

Reboot when it finishes.

## 2. Install Docker Desktop

Install Docker Desktop for Windows, using the WSL2 backend, then start it and confirm:

```powershell
docker version
```

## 3. Set the LLM provider and key

Session-only, in the PowerShell you'll run Strix from (never commit a real key):

```powershell
$env:STRIX_LLM   = "anthropic/claude-sonnet-5"
$env:LLM_API_KEY = "<your key>"
```

## 4. Run the scan

Once steps 1–3 are done, follow `docs/security/strix-report.md` for the exact scan
commands, the test-account brief (`strix-instructions.md`), and where findings get
recorded.
