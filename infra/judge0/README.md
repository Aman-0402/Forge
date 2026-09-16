# Judge0 (code execution sandbox)

Forge runs student code in [Judge0 CE](https://github.com/judge0/judge0) 1.13.1. The backend talks to its REST API; browsers never reach it.

## One-time setup on Windows 11 Home

1. **Install WSL2** (PowerShell as Administrator), then reboot:
   ```powershell
   wsl --install
   ```
2. **Install Docker Desktop** from https://www.docker.com/products/docker-desktop/ and choose the WSL2 backend. Start it and wait until it says "Engine running".
3. **Switch WSL2 to cgroup v1.** Judge0 1.13 sandboxes with `isolate`, which needs cgroup v1. Create or edit `%UserProfile%\.wslconfig`:
   ```ini
   [wsl2]
   kernelCommandLine = cgroup_no_v1=all systemd.unified_cgroup_hierarchy=0
   ```
   Then restart WSL and Docker Desktop:
   ```powershell
   wsl --shutdown
   ```
   If submissions later fail with `No such file or directory @ rb_sysopen - /box/script.py`, this step did not take effect.
4. **Check Docker:**
   ```powershell
   docker run --rm hello-world
   ```

## Start Judge0

```powershell
cd infra\judge0
.\setup.ps1            # creates judge0.conf with random secrets, prints the API token
docker compose up -d
docker compose ps      # server, workers, db, redis should be running
```

Copy the two lines printed by `setup.ps1` into `backend/.env`:

```
JUDGE0_URL=http://127.0.0.1:2358
JUDGE0_AUTH_TOKEN=<token>
```

## Verify

```powershell
$h = @{ "X-Auth-Token" = "<token>" }
Invoke-RestMethod http://127.0.0.1:2358/about -Headers $h
Invoke-RestMethod http://127.0.0.1:2358/languages -Headers $h | Select-Object -First 5
```

Then from the backend:

```powershell
cd backend
uv run python manage.py seed_languages          # Python, C, C++, Java, JavaScript
uv run python manage.py judge0_check            # runs "hello" in every enabled language
uv run pytest -m judge0                         # live integration tests (skipped when Judge0 is down)
```

## Day to day

```powershell
docker compose stop     # stop without losing data
docker compose start
docker compose logs -f workers
docker compose down -v  # remove everything, including the Judge0 database
```

## Security notes

- The API port is bound to `127.0.0.1` only. In production, keep Judge0 on a private network reachable only by the backend.
- `judge0.conf` holds secrets and is gitignored. Only `judge0.conf.example` is committed.
- Judge0 containers run `privileged` because `isolate` needs it. Run them on a host dedicated to code execution in production.
