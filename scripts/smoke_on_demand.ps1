<#
On-demand smoke runner with:
- rate limit (2 min)
- lock (no parallel runs)
- Telegram start/finish messages via clawdbot
Uses scripts/e2e_always_on_config.json for Telegram target.
Artifacts:
  scripts/_artifacts/smoke_on_demand_state.json
  scripts/_artifacts/smoke_on_demand.lock
  scripts/_artifacts/smoke_last.json (written by smoke.ps1)
  scripts/_artifacts/smoke_fail_*.log (written by smoke.ps1 on fail)
#>

param(
  [int]$RateLimitSeconds = 120
)

$ErrorActionPreference = 'Stop'

try {
  [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
  [Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
  $OutputEncoding = [System.Text.UTF8Encoding]::new($false)
} catch {}

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

function Tg([string]$channel, [string]$target, [string]$text) {
  & clawdbot message send --channel $channel --target $target --message $text | Out-Null
}

$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$cfgPath = Join-Path $PSScriptRoot 'e2e_always_on_config.json'
$artDir = Join-Path $PSScriptRoot '_artifacts'
$statePath = Join-Path $artDir 'smoke_on_demand_state.json'
$lockPath = Join-Path $artDir 'smoke_on_demand.lock'
$e2eLock = Join-Path $artDir 'e2e_on_demand.lock'
$lastPath = Join-Path $artDir 'smoke_last.json'

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
  if (Test-Path -LiteralPath $e2eLock) { Tg $channel $target "SMOKE busy: e2e running"; exit 0 }

  $state = Load-JsonOrDefault $statePath ([pscustomobject]@{ last_run_unix = 0 })
  $nowUnix = [int][DateTimeOffset]::Now.ToUnixTimeSeconds()
  $elapsed = $nowUnix - [int]$state.last_run_unix
  if ($elapsed -lt $RateLimitSeconds) {
    $wait = $RateLimitSeconds - $elapsed
    Tg $channel $target ("SMOKE rate-limited; try again in {0}s" -f $wait)
    exit 0
  }

  $state.last_run_unix = $nowUnix
  Save-Json $statePath $state

  $t0 = (Get-Date).ToString('s')
  Tg $channel $target "SMOKE start; time=$t0"

  Push-Location $repo
  try {
    $smoke = Join-Path $repo 'scripts\\smoke.ps1'
    $null = & powershell -NoProfile -ExecutionPolicy Bypass -File $smoke
  } finally {
    Pop-Location -ErrorAction SilentlyContinue
  }

  $j = $null
  if (Test-Path -LiteralPath $lastPath) {
    $j = Get-Content -Raw -LiteralPath $lastPath | ConvertFrom-Json
  }

  $t1 = (Get-Date).ToString('s')
  if ($j -and $j.ok -eq $true) {
    Tg $channel $target ("SMOKE success; time={0}; duration_ms={1}; health_ok={2}; wf={3}; status={4}/{5}" -f $t1,$j.duration_ms,$j.health.ok,$j.workflow.wf_id,$j.workflow.final_status,$j.workflow.final_state)
    exit 0
  }

  if (-not $j) {
    Tg $channel $target "SMOKE fail; time=$t1; reason=smoke_last_missing"
    exit 1
  }

  $fl = $j.fail_log
  if ($fl) { $fl = ([string]$fl) -replace '\\','/' }
  Tg $channel $target ("SMOKE fail; time={0}; duration_ms={1}; health_ok={2}; wf={3}; status={4}/{5}; fail_log={6}; error={7}" -f $t1,$j.duration_ms,$j.health.ok,$j.workflow.wf_id,$j.workflow.final_status,$j.workflow.final_state,$fl,$j.error)
  exit 1
} finally {
  Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
}
