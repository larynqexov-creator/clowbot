# ClowBot (local MVP)

Windows PowerShell runbook (no make/chmod):

## Start
```powershell
cd C:\Users\maste\clawd\clowbot

# Create local docker env file
Copy-Item .\.env.docker.example .\.env.docker

docker compose pull
docker compose up -d --build
```

## Migrations
```powershell
docker compose run --rm api alembic upgrade head
```

## Seed
```powershell
docker compose run --rm api python -m app.util.ids
```

## Health
PowerShell has a `curl` alias, so use **curl.exe**:
```powershell
curl.exe -sS http://localhost:8000/health
```
Expected: `ok=true` and `deps.* = true`.

## Mindmap (Jarvis layer)
```powershell
curl.exe -sS http://localhost:8000/mindmap/overview
```
Custom mindmaps (requires headers `X-Tenant-Id` + `X-User-Id`):
```powershell
curl.exe -sS -X POST http://localhost:8000/mindmap/custom `
  -H "X-Tenant-Id: <tenant_id>" -H "X-User-Id: seed-user" -H "Content-Type: application/json" `
  -d '{"title":"demo","mermaid":"flowchart TD\nA-->B"}'

curl.exe -sS http://localhost:8000/mindmap/custom/latest -H "X-Tenant-Id: <tenant_id>" -H "X-User-Id: seed-user"
```

## Mindmap UI (как в Mind Elixir)
В репозитории есть визуальная mindmap-страница (viewer):
- `docs/mindmap/index.html`
- `docs/mindmap/mindmap.json`

Открыть локально можно просто файлом (или через любой статический сервер). Для GitHub Pages можно будет включить позже.

## Telegram (optional integration for Outbox)
Outbox dispatcher can **really send** messages when `channel=telegram`, if env vars are set:
- `TELEGRAM_BOT_TOKEN` (from @BotFather)
- `TELEGRAM_ALLOWLIST_CHATS` (comma-separated: `@channel,123456789`)
- `TELEGRAM_DEFAULT_CHAT` (default target if ToolRegistry action doesn't specify `to`; default is `95576236`)

Without these, dispatcher stays in STUB mode and marks messages as `STUB_SENT`.

## Create tenant + run workflow
Option 1 (recommended): run the script:
```powershell
# waits up to 120s by default
powershell -ExecutionPolicy Bypass -File .\scripts\run_workflow_unique.ps1

# or override timeout
powershell -ExecutionPolicy Bypass -File .\scripts\run_workflow_unique.ps1 -TimeoutSeconds 180
```

Option 2 (manual with Invoke-RestMethod):
```powershell
$tenant = Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/admin/tenants' `
  -Headers @{ 'X-Admin-Token'='change-me-admin-token' } `
  -ContentType 'application/json' `
  -Body '{"name":"demo-tenant"}'

$tenantId = $tenant.id

$wf = Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/science/grants/run' `
  -Headers @{ 'X-Tenant-Id'=$tenantId; 'X-User-Id'='seed-user' } `
  -ContentType 'application/json' `
  -Body '{}'

$wfId = $wf.workflow_id

Invoke-RestMethod -Method Get -Uri ("http://localhost:8000/science/grants/workflows/$wfId") `
  -Headers @{ 'X-Tenant-Id'=$tenantId; 'X-User-Id'='seed-user' }
```

## Telegram ops (commands)
The bot listens only in `TelegramTarget` (see `scripts/e2e_always_on_config.json`).

Commands:
- `help` / `menu` / `?` → short menu
- `status` → mobile-first multi-line status (gateway + API health + deps + last smoke/e2e)
- `smoke` → quick workflow run (fast signal)
- `e2e` → full end-to-end run (slower, heavier)

### smoke vs e2e
- **smoke**: quick “is it alive?” check.
- **e2e**: full pipeline; rate-limited and locked to avoid parallel runs.

### Artifacts / logs
- `scripts/_artifacts/`
  - `status_state.json`, `status_fail_*.log`
  - `smoke_on_demand_state.json`, `smoke_on_demand.lock`, `smoke_last.json`, `smoke_fail_*.log`
  - `e2e_on_demand_state.json`, `e2e_on_demand.lock`, `e2e_last.json`, `e2e_fail_*.log`
  - `help_state.json`, `help.lock`
- `scripts/logs/`
  - `gateway_startup.log`, `smoke_startup.log`, `telegram_router.log`, ...

### Scheduled Tasks (Windows)
Created by scripts:
- `Clawdbot Gateway Startup` → `scripts/gateway_startup.log.cmd` (ONSTART)
- `Clowbot Smoke Startup` → `scripts/smoke_startup_wrapper.cmd` (ONSTART; 180s delay)
- `Clowbot E2E Nightly` → `scripts/e2e_always_on.ps1` (repeats every ~6h)

## Notes / anti-footguns
- Qdrant/MinIO ports are **not published to host** to avoid port collisions (they are reachable from other containers via service names).
- `deps_ready` gate waits for Postgres/Redis and then probes Qdrant/MinIO before starting API/worker (reduces race/flakiness).
- `/admin/tenants` is idempotent: create-or-get by `name` (no 500 on unique collisions).
- This repo is public: `.env.docker` is **gitignored**. Use `.env.docker.example` as a template.
