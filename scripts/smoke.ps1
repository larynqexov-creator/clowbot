<#
Smoke check for ClowBot (safe, no downtime).
- docker compose up -d (no down)
- quick /health
- lightweight workflow POST/GET
Artifacts:
  scripts/_artifacts/smoke_last.json
  scripts/_artifacts/smoke_fail_*.log (only on failure)
Output:
  one line: SMOKE_JSON=...
Exit codes:
  0 ok, 1 fail
#>

$ErrorActionPreference = 'Stop'

try {
  [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
  [Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
  $OutputEncoding = [System.Text.UTF8Encoding]::new($false)
} catch {}

function Invoke-Step {
  param([string]$Name, [scriptblock]$Script)
  try { & $Script } catch { throw "STEP_FAILED::$Name::$($_.Exception.Message)" }
}

function Dump-ComposeStateAndLogs {
  param([string]$RepoRoot, [string]$FailLogPath)
  try {
    Push-Location $RepoRoot
    $dir = Split-Path -Parent $FailLogPath
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }

    "# ClowBot smoke failure dump`n# time=" + (Get-Date).ToString('s') + "`n" | Set-Content -LiteralPath $FailLogPath -Encoding UTF8

    "`n--- docker compose ps ---`n" | Add-Content -LiteralPath $FailLogPath -Encoding UTF8
    (docker compose ps | Out-String) | Add-Content -LiteralPath $FailLogPath -Encoding UTF8

    "`n--- docker compose logs --tail=200 ---`n" | Add-Content -LiteralPath $FailLogPath -Encoding UTF8
    (docker compose logs --tail=200 api worker postgres redis qdrant minio | Out-String) | Add-Content -LiteralPath $FailLogPath -Encoding UTF8
  } catch {
  } finally {
    Pop-Location -ErrorAction SilentlyContinue
  }
}

$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$artDir = Join-Path $PSScriptRoot '_artifacts'
$lastJsonPath = Join-Path $artDir 'smoke_last.json'

$startedAt = Get-Date

$result = [ordered]@{
  ok = $false
  duration_ms = $null
  health = $null
  workflow = [ordered]@{ tenant_id = $null; wf_id = $null; final_status = $null; final_state = $null }
  error = $null
  fail_log = $null
}

try {
  Push-Location $repo

  Invoke-Step -Name 'compose_up' -Script {
    docker compose up -d | Out-Host
  }

  Invoke-Step -Name 'health' -Script {
    $hraw = (curl.exe -sS http://localhost:8000/health)
    $h = $hraw | ConvertFrom-Json
    $result.health = $h
    if (-not $h.ok) { throw 'health.ok is false' }
    foreach ($k in @('postgres','redis','qdrant','minio')) {
      if (-not $h.deps.$k) { throw "health.deps.$k is false" }
    }
  }

  Invoke-Step -Name 'tenant_id' -Script {
    # generate an ephemeral tenant id (cheap). output must be a single UUID.
    $tenant = (docker compose run --rm api python -m app.util.ids) | Out-String
    $tenant = $tenant.Trim()
    if ($tenant -notmatch '^[0-9a-fA-F-]{36}$') { throw "unexpected tenant id: $tenant" }
    $result.workflow.tenant_id = $tenant
  }

  Invoke-Step -Name 'workflow_post' -Script {
    $tenant = $result.workflow.tenant_id
    $user = 'smoke-user'
    $resp = curl.exe -sS -X POST http://localhost:8000/science/grants/run -H "X-Tenant-Id: $tenant" -H "X-User-Id: $user"
    $j = $resp | ConvertFrom-Json
    if (-not $j.workflow_id) { throw "missing workflow_id" }
    $result.workflow.wf_id = [string]$j.workflow_id
  }

  Invoke-Step -Name 'workflow_poll' -Script {
    $tenant = $result.workflow.tenant_id
    $user = 'smoke-user'
    $wf = $result.workflow.wf_id
    $deadline = (Get-Date).AddSeconds(30)
    while ($true) {
      $resp = curl.exe -sS http://localhost:8000/science/grants/workflows/$wf -H "X-Tenant-Id: $tenant" -H "X-User-Id: $user"
      $j = $resp | ConvertFrom-Json
      $result.workflow.final_status = [string]$j.status
      $result.workflow.final_state = [string]$j.state
      if ($j.status -eq 'COMPLETED') { break }
      if ((Get-Date) -gt $deadline) { throw "workflow timeout; status=$($j.status) state=$($j.state)" }
      Start-Sleep -Milliseconds 500
    }
  }

  $result.ok = $true
} catch {
  $result.ok = $false
  $result.error = $_.Exception.Message

  try {
    if (-not (Test-Path -LiteralPath $artDir)) { New-Item -ItemType Directory -Path $artDir | Out-Null }
    $ts = (Get-Date).ToString('yyyyMMdd-HHmmss')
    $fail = Join-Path $artDir ("smoke_fail_$ts.log")
    Dump-ComposeStateAndLogs -RepoRoot $repo -FailLogPath $fail
    $result.fail_log = $fail
  } catch {}
} finally {
  $result.duration_ms = [int]([TimeSpan]((Get-Date) - $startedAt)).TotalMilliseconds

  try {
    if (-not (Test-Path -LiteralPath $artDir)) { New-Item -ItemType Directory -Path $artDir | Out-Null }
    ($result | ConvertTo-Json -Depth 10) | Set-Content -LiteralPath $lastJsonPath -Encoding UTF8
  } catch {}

  Pop-Location -ErrorAction SilentlyContinue
}

$compact = ($result | ConvertTo-Json -Depth 10 -Compress)
Write-Output ("SMOKE_JSON=$compact")
if ($result.ok) { exit 0 } else { exit 1 }
