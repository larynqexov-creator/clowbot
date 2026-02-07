# ClowBot (local MVP)

Windows PowerShell runbook (no make/chmod):

## Start
```powershell
cd C:\Users\maste\clawd\clowbot
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

## Create tenant + run workflow
Option 1 (recommended): run the script:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_workflow_unique.ps1
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

## Notes / anti-footguns
- Qdrant/MinIO ports are **not published to host** to avoid port collisions (they are reachable from other containers via service names).
- `deps_ready` gate waits for Postgres/Redis and then probes Qdrant/MinIO before starting API/worker (reduces race/flakiness).
- `/admin/tenants` is idempotent: create-or-get by `name` (no 500 on unique collisions).
