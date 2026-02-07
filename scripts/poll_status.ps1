param(
  [Parameter(Mandatory=$true)][string]$TenantId,
  [Parameter(Mandatory=$true)][string]$WorkflowId
)
$ErrorActionPreference = 'Stop'

for ($i=1; $i -le 60; $i++) {
  $st = Invoke-RestMethod -Method Get -Uri ("http://localhost:8000/science/grants/workflows/$WorkflowId") `
    -Headers @{ 'X-Tenant-Id'=$TenantId; 'X-User-Id'='seed-user' }
  if ($st.state -eq 'NOTIFIED' -or $st.status -eq 'COMPLETED') {
    $st | ConvertTo-Json -Depth 6
    exit 0
  }
  Start-Sleep -Seconds 1
}
$st | ConvertTo-Json -Depth 6
exit 1
