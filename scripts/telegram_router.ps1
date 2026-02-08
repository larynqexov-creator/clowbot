<#
Telegram inbound router for ClowBot ops.
- Polls Telegram getUpdates using the bot token from ~/.clawdbot/clawdbot.json
- Accepts ONLY:
    chat.id == TelegramTarget (from scripts/e2e_always_on_config.json)
    text command in: status|smoke|e2e|help|menu|?
- Lock: prevents parallel runs
- Per-command rate-limit/locks are handled by scripts/*_on_demand.ps1
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

function Safe-TgFailLogPath($p) {
  # Avoid backslash escaping issues in chat clients; prefer repo-relative forward-slash path.
  if (-not $p) { return $null }
  $s = [string]$p
  $s = $s -replace '\\','/'
  return $s
}

$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$cfgPath = Join-Path $PSScriptRoot 'e2e_always_on_config.json'
$artDir = Join-Path $PSScriptRoot '_artifacts'
$statePath = Join-Path $artDir 'telegram_router_state.json'
$lockPath = Join-Path $artDir 'telegram_router.lock'
$e2eLastPath = Join-Path $artDir 'e2e_last.json'

$handlers = @{
  'status' = (Join-Path $PSScriptRoot 'status_on_demand.ps1')
  'smoke'  = (Join-Path $PSScriptRoot 'smoke_on_demand.ps1')
  'e2e'    = (Join-Path $PSScriptRoot 'e2e_on_demand.ps1')
  'help'   = (Join-Path $PSScriptRoot 'help_on_demand.ps1')
  'menu'   = (Join-Path $PSScriptRoot 'help_on_demand.ps1')
  '?'      = (Join-Path $PSScriptRoot 'help_on_demand.ps1')
}

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

    $cmd = ''
    try {
      $cmd = ([string]$text).Trim()
      if ($cmd.StartsWith('/')) { $cmd = $cmd.Substring(1) }
      $cmd = $cmd.ToLowerInvariant()
    } catch {}

    if (-not $handlers.ContainsKey($cmd)) { continue }

    $script = [string]$handlers[$cmd]
    if (-not (Test-Path -LiteralPath $script)) {
      Send-Telegram $tgChannel $tgTarget ("Unknown handler for '{0}'" -f $cmd)
      continue
    }

    # Run the appropriate on-demand script; it sends its own TG messages (locks/rate-limits inside).
    Push-Location $repo
    try {
      $null = & powershell -NoProfile -ExecutionPolicy Bypass -File $script
    } finally {
      Pop-Location -ErrorAction SilentlyContinue
    }
  }

  Save-Json $statePath $state
} finally {
  Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
}
