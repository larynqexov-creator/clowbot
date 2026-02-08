<#
On-demand STATUS runner with:
- rate limit (60s)
- lock (no parallel runs)
- busy-check: e2e_on_demand.lock / smoke_on_demand.lock
- Telegram start/finish messages via clawdbot
Uses scripts/e2e_always_on_config.json for Telegram target.
Artifacts:
  scripts/_artifacts/status_state.json
  scripts/_artifacts/status.lock
  scripts/_artifacts/status_fail_*.log
#>

param(
  [int]$RateLimitSeconds = 60
)

$ErrorActionPreference = 'Stop'

try {
  $utf8 = [System.Text.UTF8Encoding]::new($false)
  [Console]::OutputEncoding = $utf8
  [Console]::InputEncoding = $utf8
  $OutputEncoding = $utf8
} catch {}

function Ensure-Dir([string]$p) {
  if (-not (Test-Path -LiteralPath $p)) { New-Item -ItemType Directory -Path $p | Out-Null }
}

function Load-JsonOrDefault([string]$path, $default) {
  try {
    if (Test-Path -LiteralPath $path) {
      return (Get-Content -Raw -LiteralPath $path | ConvertFrom-Json)
    }
  } catch {}
  return $default
}

function Save-Json([string]$path, $obj) {
  $dir = Split-Path -Parent $path
  if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
  ($obj | ConvertTo-Json -Depth 10) | Set-Content -LiteralPath $path -Encoding UTF8
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

function Tg([string]$channel, [string]$target, [string]$text) {
  & clawdbot message send --channel $channel --target $target --message $text | Out-Null
}

$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$cfgPath = Join-Path $PSScriptRoot 'e2e_always_on_config.json'
$artDir = Join-Path $PSScriptRoot '_artifacts'
$statePath = Join-Path $artDir 'status_state.json'
$lockPath = Join-Path $artDir 'status.lock'
$e2eLock = Join-Path $artDir 'e2e_on_demand.lock'
$smokeLock = Join-Path $artDir 'smoke_on_demand.lock'

Ensure-Dir $artDir

if (-not (Test-Path -LiteralPath $cfgPath)) {
  throw "Missing config: $cfgPath"
}
$cfg = Get-Content -Raw -LiteralPath $cfgPath | ConvertFrom-Json
$channel = [string]$cfg.TelegramChannel
if (-not $channel) { $channel = 'telegram' }
$target = [string]$cfg.TelegramTarget

# lock
try {
  New-Item -ItemType File -Path $lockPath -Force -ErrorAction Stop | Out-Null
} catch {
  exit 0
}

try {
  if (Test-Path -LiteralPath $e2eLock) { Tg $channel $target "STATUS busy: e2e running"; exit 0 }
  if (Test-Path -LiteralPath $smokeLock) { Tg $channel $target "STATUS busy: smoke running"; exit 0 }

  $state = Load-JsonOrDefault $statePath ([pscustomobject]@{ last_run_unix = 0 })
  $nowUnix = [int][DateTimeOffset]::Now.ToUnixTimeSeconds()
  $elapsed = $nowUnix - [int]$state.last_run_unix
  if ($elapsed -lt $RateLimitSeconds) {
    $wait = $RateLimitSeconds - $elapsed
    Tg $channel $target ("STATUS rate-limited; try again in {0}s" -f $wait)
    exit 0
  }
  $state.last_run_unix = $nowUnix
  Save-Json $statePath $state

  $t0 = (Get-Date).ToString('s')
  Tg $channel $target "STATUS start; time=$t0"

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

    # health (clowbot)
    $health = $null
    try {
      $hraw = (curl.exe --max-time 2 -sS http://localhost:8000/health)
      if ($hraw) { $health = $hraw | ConvertFrom-Json }
    } catch {}

    $t1 = (Get-Date).ToString('s')
    if ($gwOk -and $health -and $health.ok -eq $true) {
      Tg $channel $target ("STATUS ok; time={0}; gw_pid={1}; health_ok={2}; deps=pg:{3} r:{4} q:{5} m:{6}" -f $t1,$gwPid,$health.ok,$health.deps.postgres,$health.deps.redis,$health.deps.qdrant,$health.deps.minio)
      exit 0
    }

    # include last artifacts snapshot for debugging
    $smokePath = Join-Path $artDir 'smoke_last.json'
    $e2ePath = Join-Path $artDir 'e2e_last.json'
    $smoke = Read-JsonOrNull $smokePath
    $e2e = Read-JsonOrNull $e2ePath
    $smokeTime = File-TimeOrNull $smokePath
    $e2eTime = File-TimeOrNull $e2ePath

    $extra = ""
    if ($smoke) { $extra += (" smoke_last_ok={0} smoke_time={1}" -f $smoke.ok,$smokeTime) }
    if ($e2e) { $extra += (" e2e_last_ok={0} e2e_time={1}" -f $e2e.ok,$e2eTime) }

    Tg $channel $target ("STATUS fail; time={0}; gw_ok={1}; gw_pid={2}; health_ok={3}; fail_log=n/a{4}" -f $t1,$gwOk,$gwPid,($health.ok),$extra)
    exit 1
  } finally {
    Pop-Location -ErrorAction SilentlyContinue
  }
} catch {
  $ts = (Get-Date).ToString('yyyyMMdd-HHmmss')
  $fail = Join-Path $artDir ("status_fail_$ts.log")
  try {
    ("STATUS exception: " + $_.Exception.Message + "`n") | Set-Content -LiteralPath $fail -Encoding UTF8
  } catch {}
  $t1 = (Get-Date).ToString('s')
  try {
    Tg $channel $target ("STATUS fail; time={0}; fail_log={1}; error={2}" -f $t1,(SafePath $fail),$_.Exception.Message)
  } catch {}
  exit 1
} finally {
  Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
}
