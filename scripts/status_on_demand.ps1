<#
Status on-demand (no polling).
- Lock: scripts/_artifacts/status.lock
- Busy-check: e2e_on_demand.lock / smoke_on_demand.lock
- Outputs 1-3 lines to stdout (for TG reply by caller)
- On error: writes scripts/_artifacts/status_fail_*.log and prints a short failure line
#>

$ErrorActionPreference = 'Stop'

try {
  $utf8 = [System.Text.UTF8Encoding]::new($false)
  [Console]::OutputEncoding = $utf8
  [Console]::InputEncoding = $utf8
  $OutputEncoding = $utf8
} catch {}

$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$artDir = Join-Path $PSScriptRoot '_artifacts'
$lockPath = Join-Path $artDir 'status.lock'
$e2eLock = Join-Path $artDir 'e2e_on_demand.lock'
$smokeLock = Join-Path $artDir 'smoke_on_demand.lock'

function Ensure-Dir([string]$p) {
  if (-not (Test-Path -LiteralPath $p)) { New-Item -ItemType Directory -Path $p | Out-Null }
}

function Read-JsonOrNull([string]$p) {
  try {
    if (Test-Path -LiteralPath $p) {
      return (Get-Content -Raw -LiteralPath $p | ConvertFrom-Json)
    }
  } catch {}
  return $null
}

function File-TimeOrNull([string]$p) {
  try {
    if (Test-Path -LiteralPath $p) {
      return (Get-Item -LiteralPath $p).LastWriteTime.ToString('s')
    }
  } catch {}
  return $null
}

function SafePath([string]$p) {
  if (-not $p) { return $null }
  return ([string]$p) -replace '\\','/'
}

Ensure-Dir $artDir

# Lock
try {
  New-Item -ItemType File -Path $lockPath -Force -ErrorAction Stop | Out-Null
} catch {
  Write-Output "STATUS busy: status already running"
  exit 0
}

try {
  if (Test-Path -LiteralPath $e2eLock) { Write-Output "STATUS busy: e2e running"; exit 0 }
  if (Test-Path -LiteralPath $smokeLock) { Write-Output "STATUS busy: smoke running"; exit 0 }

  Push-Location $repo
  try {
    # gateway
    $gw = $null
    try {
      $gwRaw = (clawdbot gateway status --json | Out-String)
      if ($gwRaw) { $gw = $gwRaw | ConvertFrom-Json }
    } catch {}

    $gwPid = $null
    $gwOk = $false
    try {
      $gwOk = [bool]($gw.rpc.ok)
      if ($gw.port.listeners -and $gw.port.listeners.Count -gt 0) { $gwPid = $gw.port.listeners[0].pid }
    } catch {}

    # compose ps (short)
    $compose = ""
    try {
      $compose = (docker compose ps --format json | Out-String)
    } catch {
      # fallback
      $compose = (docker compose ps | Out-String)
    }

    # health
    $health = $null
    try {
      $hraw = (curl.exe --max-time 2 -sS http://localhost:8000/health)
      if ($hraw) { $health = $hraw | ConvertFrom-Json }
    } catch {}

    # last artifacts
    $smokePath = Join-Path $artDir 'smoke_last.json'
    $e2ePath = Join-Path $artDir 'e2e_last.json'

    $smoke = Read-JsonOrNull $smokePath
    $e2e = Read-JsonOrNull $e2ePath

    $smokeTime = File-TimeOrNull $smokePath
    $e2eTime = File-TimeOrNull $e2ePath

    $line1 = "GW ok=$gwOk pid=$gwPid"

    # Summarize compose by grepping key services from table output (human-friendly)
    $psLine = "compose:"
    foreach ($svc in @('api','worker','postgres','redis','qdrant','minio')) {
      if ($compose -match "clowbot-$svc") {
        $psLine += " $svc=up"
      } else {
        $psLine += " $svc=?"
      }
    }

    $hLine = "health:"
    if ($health) {
      $hLine += " ok=$($health.ok) deps=pg:$($health.deps.postgres) r:$($health.deps.redis) q:$($health.deps.qdrant) m:$($health.deps.minio)"
    } else {
      $hLine += " n/a"
    }

    $sLine = "smoke_last:"
    if ($smoke) {
      $sLine += " ok=$($smoke.ok) time=$smokeTime wf=$($smoke.workflow.wf_id) $($smoke.workflow.final_status)/$($smoke.workflow.final_state)"
    } else {
      $sLine += " n/a"
    }

    $eLine = "e2e_last:"
    if ($e2e) {
      $eLine += " ok=$($e2e.ok) time=$e2eTime wf=$($e2e.workflow.wf_id) $($e2e.workflow.final_status)/$($e2e.workflow.final_state)"
      if ($e2e.fail_log) { $eLine += " fail_log=$(SafePath $e2e.fail_log)" }
    } else {
      $eLine += " n/a"
    }

    # 1-3 lines total (pack)
    Write-Output $line1
    Write-Output "$psLine; $hLine"
    Write-Output "$sLine; $eLine"
  } finally {
    Pop-Location -ErrorAction SilentlyContinue
  }
} catch {
  $ts = (Get-Date).ToString('yyyyMMdd-HHmmss')
  $fail = Join-Path $artDir ("status_fail_$ts.log")
  try {
    ("STATUS exception: " + $_.Exception.Message + "`n") | Set-Content -LiteralPath $fail -Encoding UTF8
  } catch {}
  Write-Output ("STATUS fail; fail_log={0}" -f (SafePath $fail))
  exit 1
} finally {
  Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
}
