<#
E2E check script for ClowBot.
Runs:
  - git clean check
  - docker version + docker compose version
  - docker compose down/up
  - migrations
  - seed tenant id
  - health
  - workflow unique run
Prints one compact JSON summary at the end.
Exit codes: 0=ok, 1=fail
#>

$ErrorActionPreference = 'Stop'

# Force UTF-8 output (avoid mojibake)
try {
  [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
  [Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
  $OutputEncoding = [System.Text.UTF8Encoding]::new($false)
} catch {}

function Invoke-Step {
  param(
    [Parameter(Mandatory=$true)][string]$Name,
    [Parameter(Mandatory=$true)][scriptblock]$Script
  )
  try {
    & $Script
  } catch {
    throw "STEP_FAILED::$Name::$($_.Exception.Message)"
  }
}

function Dump-ComposeStateAndLogs {
  param(
    [Parameter(Mandatory=$true)][string]$RepoRoot,
    [Parameter(Mandatory=$true)][string]$FailLogPath
  )
  try {
    Push-Location $RepoRoot
    $dir = Split-Path -Parent $FailLogPath
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }

    $header = "# ClowBot E2E failure dump\n# time=" + (Get-Date).ToString('s') + "\n\n"
    Set-Content -LiteralPath $FailLogPath -Value $header -Encoding UTF8

    Add-Content -LiteralPath $FailLogPath -Value "--- docker compose ps ---\n" -Encoding UTF8
    (docker compose ps | Out-String) | Add-Content -LiteralPath $FailLogPath -Encoding UTF8

    Add-Content -LiteralPath $FailLogPath -Value "\n--- docker compose logs --tail=200 ---\n" -Encoding UTF8
    (docker compose logs --tail=200 api worker postgres redis qdrant minio | Out-String) | Add-Content -LiteralPath $FailLogPath -Encoding UTF8
  } catch {
    # best-effort
  } finally {
    Pop-Location -ErrorAction SilentlyContinue
  }
}

$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$startedAt = Get-Date

$artDir = Join-Path $PSScriptRoot '_artifacts'
$lastJsonPath = Join-Path $artDir 'e2e_last.json'
$failLogPath = $null

$result = [ordered]@{
  ok = $false
  duration_ms = $null
  versions = [ordered]@{
    docker = $null
    compose = $null
  }
  health = $null
  seed_tenant_id = $null
  workflow = [ordered]@{
    tenant_id = $null
    wf_id = $null
    final_status = $null
    final_state = $null
    grants_count = $null
  }
  error = $null
  fail_log = $null
}

try {
  Push-Location $repo

  Invoke-Step -Name 'git_clean' -Script {
    $dirty = (git status --porcelain)
    if ($dirty -and $dirty.Trim().Length -gt 0) {
      throw "git working tree not clean: $dirty"
    }
  }

  Invoke-Step -Name 'docker_version' -Script {
    $dv = (docker version --format '{{json .}}')
    if (-not $dv) { throw 'no output' }
    $dvo = $dv | ConvertFrom-Json
    $result.versions.docker = [ordered]@{
      client = $dvo.Client.Version
      server = $dvo.Server.Version
    }
  }

  Invoke-Step -Name 'compose_version' -Script {
    $cv = (docker compose version --short)
    $result.versions.compose = $cv
  }

  Invoke-Step -Name 'compose_down' -Script {
    docker compose down --remove-orphans | Out-Host
  }

  Invoke-Step -Name 'compose_up' -Script {
    docker compose up -d --build | Out-Host
  }

  Invoke-Step -Name 'compose_ps' -Script {
    docker compose ps | Out-Host
  }

  Invoke-Step -Name 'migrate' -Script {
    docker compose run --rm api alembic upgrade head | Out-Host
  }

  Invoke-Step -Name 'seed_ids' -Script {
    $seed = (docker compose run --rm api python -m app.util.ids)
    $seed = ($seed | Out-String).Trim()
    if ($seed -notmatch '^[0-9a-fA-F-]{36}$') {
      throw "unexpected seed output: $seed"
    }
    $result.seed_tenant_id = $seed
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

  Invoke-Step -Name 'workflow' -Script {
    $out = (powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo 'scripts\run_workflow_unique.ps1') -TimeoutSeconds 120) | Out-String

    $mTenant = [regex]::Match($out, 'TENANT_ID=([0-9a-fA-F-]{36})')
    $mWf = [regex]::Match($out, 'WF_ID=([0-9a-fA-F-]{36})')
    $mStatus = [regex]::Match($out, 'FINAL_STATUS=([A-Z_]+)')
    $mState = [regex]::Match($out, 'FINAL_STATE=([A-Z_]+)')
    $mGrants = [regex]::Match($out, 'ARTIFACTS\.grants\.count=(\d+)')

    if (-not $mTenant.Success) { throw 'missing TENANT_ID in workflow output' }
    if (-not $mWf.Success) { throw 'missing WF_ID in workflow output' }
    if (-not $mStatus.Success) { throw 'missing FINAL_STATUS in workflow output' }
    if (-not $mState.Success) { throw 'missing FINAL_STATE in workflow output' }
    if (-not $mGrants.Success) { throw 'missing ARTIFACTS.grants.count in workflow output' }

    $result.workflow.tenant_id = $mTenant.Groups[1].Value
    $result.workflow.wf_id = $mWf.Groups[1].Value
    $result.workflow.final_status = $mStatus.Groups[1].Value
    $result.workflow.final_state = $mState.Groups[1].Value
    $result.workflow.grants_count = [int]$mGrants.Groups[1].Value
  }

  $result.ok = $true
} catch {
  $result.ok = $false
  $result.error = $_.Exception.Message

  try {
    if (-not (Test-Path -LiteralPath $artDir)) { New-Item -ItemType Directory -Path $artDir | Out-Null }
    $ts = (Get-Date).ToString('yyyyMMdd-HHmmss')
    $failLogPath = Join-Path $artDir ("e2e_fail_$ts.log")
    Dump-ComposeStateAndLogs -RepoRoot $repo -FailLogPath $failLogPath
    $result.fail_log = $failLogPath
  } catch {
    # ignore
  }
} finally {
  $result.duration_ms = [int]([TimeSpan]((Get-Date) - $startedAt)).TotalMilliseconds

  # Always persist last result
  try {
    if (-not (Test-Path -LiteralPath $artDir)) { New-Item -ItemType Directory -Path $artDir | Out-Null }
    ($result | ConvertTo-Json -Depth 10) | Set-Content -LiteralPath $lastJsonPath -Encoding UTF8
  } catch {}

  Pop-Location -ErrorAction SilentlyContinue
}

# Print exactly one compact JSON line (for CI/check usage)
$compact = ($result | ConvertTo-Json -Depth 10 -Compress)
Write-Output ("E2E_JSON=$compact")

if ($result.ok) { exit 0 } else { exit 1 }
