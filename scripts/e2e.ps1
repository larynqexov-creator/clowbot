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

function Dump-ComposeLogs {
  param([string]$RepoRoot)
  try {
    Push-Location $RepoRoot
    Write-Host "--- docker compose logs (tail=200) ---" -ForegroundColor Yellow
    docker compose logs --tail=200 api worker postgres redis
  } catch {
    # best-effort
  } finally {
    Pop-Location -ErrorAction SilentlyContinue
  }
}

$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$startedAt = Get-Date

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
  Dump-ComposeLogs -RepoRoot $repo
} finally {
  $result.duration_ms = [int]([TimeSpan]((Get-Date) - $startedAt)).TotalMilliseconds
  Pop-Location -ErrorAction SilentlyContinue
}

# Print exactly one compact JSON line (for CI/check usage)
($result | ConvertTo-Json -Depth 10 -Compress) | Write-Output

if ($result.ok) { exit 0 } else { exit 1 }
