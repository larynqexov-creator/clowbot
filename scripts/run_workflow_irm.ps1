$ErrorActionPreference = 'Stop'

$tenant = Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/admin/tenants' `
  -Headers @{ 'X-Admin-Token'='change-me-admin-token' } `
  -ContentType 'application/json' `
  -Body '{"name":"demo-tenant"}'

$tenantId = $tenant.id
Write-Output ("TENANT_ID=$tenantId")

$wf = Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/science/grants/run' `
  -Headers @{ 'X-Tenant-Id'=$tenantId; 'X-User-Id'='seed-user' } `
  -ContentType 'application/json' `
  -Body '{}'

$wfId = $wf.workflow_id
Write-Output ("WF_ID=$wfId")

$st = Invoke-RestMethod -Method Get -Uri ("http://localhost:8000/science/grants/workflows/$wfId") `
  -Headers @{ 'X-Tenant-Id'=$tenantId; 'X-User-Id'='seed-user' }

$st | ConvertTo-Json -Depth 6
