$ErrorActionPreference = 'Stop'

$t = curl.exe -f -sS -X POST http://localhost:8000/admin/tenants `
  -H 'Content-Type: application/json' `
  -H 'X-Admin-Token: change-me-admin-token' `
  -d '{"name":"demo-tenant"}'

Write-Output "TENANT_RAW=$t"
$tenantId = ($t | ConvertFrom-Json).id
if (-not $tenantId) { throw "Tenant creation failed (no id in response)" }
Write-Output ("TENANT_ID=$tenantId")

$w = curl.exe -f -sS -X POST http://localhost:8000/science/grants/run `
  -H 'Content-Type: application/json' `
  -H "X-Tenant-Id: $tenantId" `
  -H 'X-User-Id: seed-user' `
  -d '{}'

Write-Output "WF_RAW=$w"
$wfId = ($w | ConvertFrom-Json).workflow_id
if (-not $wfId) { throw "Workflow start failed (no workflow_id in response)" }
Write-Output ("WF_ID=$wfId")

$s = curl.exe -f -sS "http://localhost:8000/science/grants/workflows/$wfId" `
  -H "X-Tenant-Id: $tenantId" `
  -H 'X-User-Id: seed-user'

Write-Output "STATUS=$s"
