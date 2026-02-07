param(
  [int]$TimeoutSeconds = 120,
  [string]$BaseUrl = 'http://localhost:8000'
)
$ErrorActionPreference = 'Stop'

function Short-Json($obj) {
  return ($obj | ConvertTo-Json -Depth 8)
}

# Always use a unique name to avoid unique collisions.
$name = 'demo-tenant-' + ([guid]::NewGuid().ToString('N').Substring(0,8))
$body = '{"name":"' + $name + '"}'

$tenant = Invoke-RestMethod -Method Post -Uri ("$BaseUrl/admin/tenants") `
  -Headers @{ 'X-Admin-Token'='change-me-admin-token' } `
  -ContentType 'application/json' `
  -Body $body

$tenantId = $tenant.id
if (-not $tenantId) { throw "Tenant create failed: $(Short-Json $tenant)" }
Write-Output ("TENANT_ID=$tenantId")

$wf = Invoke-RestMethod -Method Post -Uri ("$BaseUrl/science/grants/run") `
  -Headers @{ 'X-Tenant-Id'=$tenantId; 'X-User-Id'='seed-user' } `
  -ContentType 'application/json' `
  -Body '{}'

$wfId = $wf.workflow_id
if (-not $wfId) { throw "Workflow start failed: $(Short-Json $wf)" }
Write-Output ("WF_ID=$wfId")

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$last = $null
while ((Get-Date) -lt $deadline) {
  $last = Invoke-RestMethod -Method Get -Uri ("$BaseUrl/science/grants/workflows/$wfId") `
    -Headers @{ 'X-Tenant-Id'=$tenantId; 'X-User-Id'='seed-user' }

  if ($last.status -eq 'FAILED' -or $last.state -eq 'FAILED') {
    Write-Output ("FINAL_STATUS=FAILED")
    Write-Output ("FINAL_STATE=$($last.state)")
    Write-Output ("LAST_ERROR=$($last.last_error)")
    Write-Output (Short-Json $last)
    exit 1
  }

  if ($last.status -eq 'COMPLETED' -or $last.state -eq 'NOTIFIED') {
    Write-Output ("FINAL_STATUS=$($last.status)")
    Write-Output ("FINAL_STATE=$($last.state)")

    # Print a compact summary of artifacts.
    $grantsCount = 0
    if ($last.artifacts -and $last.artifacts.grants) { $grantsCount = @($last.artifacts.grants).Count }
    Write-Output ("ARTIFACTS.grants.count=$grantsCount")

    if ($grantsCount -gt 0) {
      $first = $last.artifacts.grants[0]
      if ($first -and $first.grant_id) {
        Write-Output ("ARTIFACTS.first_grant=$($first.grant_id) $($first.title)")
      }
    }

    Write-Output (Short-Json $last)
    exit 0
  }

  Start-Sleep -Seconds 2
}

Write-Output "TIMEOUT"
if ($last) { Write-Output (Short-Json $last) }
exit 1
