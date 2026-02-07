<#
Telegram inbound router for ClowBot ops.
- Polls Telegram getUpdates using the bot token from ~/.clawdbot/clawdbot.json
- Accepts ONLY:
    chat.id == TelegramTarget (from scripts/e2e_always_on_config.json)
    text exactly 'e2e'
- Rate limit: once per 10 minutes
- Lock: prevents parallel runs
Artifacts:
  scripts/_artifacts/telegram_router_state.json
  scripts/_artifacts/telegram_router.lock
#>

$ErrorActionPreference = 'Stop'

try {
  [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
  [Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
  $OutputEncoding = [System.Text.UTF8Encoding]::new($false)
} catch {}

function Load-JsonOrNull([string]$path) {
  try {
    if (Test-Path -LiteralPath $path) {
      return (Get-Content -Raw -LiteralPath $path | ConvertFrom-Json)
    }
  } catch {}
  return $null
}

function Save-Json([string]$path, $obj) {
  $dir = Split-Path -Parent $path
  if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
  ($obj | ConvertTo-Json -Depth 10) | Set-Content -LiteralPath $path -Encoding UTF8
}

function Send-Telegram([string]$channel, [string]$target, [string]$text) {
  & clawdbot message send --channel $channel --target $target --message $text | Out-Null
}

$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$cfgPath = Join-Path $PSScriptRoot 'e2e_always_on_config.json'
$artDir = Join-Path $PSScriptRoot '_artifacts'
$statePath = Join-Path $artDir 'telegram_router_state.json'
$lockPath = Join-Path $artDir 'telegram_router.lock'
$e2eLastPath = Join-Path $artDir 'e2e_last.json'

if (-not (Test-Path -LiteralPath $cfgPath)) {
  throw "Missing config: $cfgPath"
}
$cfg = Get-Content -Raw -LiteralPath $cfgPath | ConvertFrom-Json
$tgTarget = [string]$cfg.TelegramTarget
$tgChannel = [string]$cfg.TelegramChannel
if (-not $tgChannel) { $tgChannel = 'telegram' }

$clawCfgPath = Join-Path $env:USERPROFILE '.clawdbot\clawdbot.json'
$clawCfg = Get-Content -Raw -LiteralPath $clawCfgPath | ConvertFrom-Json
$botToken = $clawCfg.channels.telegram.botToken
if (-not $botToken) { throw "Missing telegram botToken in $clawCfgPath" }

# Acquire lock (best-effort; if locked, exit quietly)
try {
  New-Item -ItemType File -Path $lockPath -Force -ErrorAction Stop | Out-Null
} catch {
  exit 0
}

try {
  $state = Load-JsonOrNull $statePath
  if (-not $state) {
    $state = [pscustomobject]@{ last_update_id = 0; last_run_unix = 0 }
  }

  $offset = [int]$state.last_update_id + 1

  $uri = "https://api.telegram.org/bot$botToken/getUpdates?offset=$offset&limit=10&timeout=0"
  $resp = Invoke-RestMethod -Method Get -Uri $uri -TimeoutSec 15
  if (-not $resp.ok) { throw "telegram getUpdates not ok" }

  $updates = @()
  if ($resp.result) { $updates = @($resp.result) }

  foreach ($u in $updates) {
    if ($u.update_id -gt $state.last_update_id) { $state.last_update_id = [int]$u.update_id }

    $m = $u.message
    if (-not $m) { continue }

    $chatId = [string]$m.chat.id
    $text = [string]$m.text

    if ($chatId -ne $tgTarget) { continue }
    if ($text -ne 'e2e') { continue }

    $nowUnix = [int][DateTimeOffset]::Now.ToUnixTimeSeconds()
    $elapsed = $nowUnix - [int]$state.last_run_unix
    if ($elapsed -lt 600) {
      $wait = 600 - $elapsed
      Send-Telegram $tgChannel $tgTarget ("E2E rate-limited; try again in {0}s" -f $wait)
      continue
    }

    $state.last_run_unix = $nowUnix
    Save-Json $statePath $state

    $t0 = (Get-Date).ToString('s')
    Send-Telegram $tgChannel $tgTarget "E2E start; time=$t0"

    Push-Location $repo
    try {
      $e2e = Join-Path $repo 'scripts\e2e.ps1'
      $null = & powershell -NoProfile -ExecutionPolicy Bypass -File $e2e
    } finally {
      Pop-Location -ErrorAction SilentlyContinue
    }

    $j = Load-JsonOrNull $e2eLastPath
    if (-not $j) {
      Send-Telegram $tgChannel $tgTarget "E2E fail; time=$((Get-Date).ToString('s')); reason=e2e_last_missing"
      continue
    }

    if ($j.ok -eq $true) {
      $t1 = (Get-Date).ToString('s')
      Send-Telegram $tgChannel $tgTarget ("E2E success; time={0}; duration_ms={1}; health_ok={2}; wf={3}; status={4}/{5}; grants_count={6}" -f $t1,$j.duration_ms,$j.health.ok,$j.workflow.wf_id,$j.workflow.final_status,$j.workflow.final_state,$j.workflow.grants_count)
    } else {
      $t1 = (Get-Date).ToString('s')
      Send-Telegram $tgChannel $tgTarget ("E2E fail; time={0}; duration_ms={1}; health_ok={2}; wf={3}; status={4}/{5}; fail_log={6}; error={7}" -f $t1,$j.duration_ms,$j.health.ok,$j.workflow.wf_id,$j.workflow.final_status,$j.workflow.final_state,$j.fail_log,$j.error)
    }
  }

  Save-Json $statePath $state
} finally {
  Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
}
