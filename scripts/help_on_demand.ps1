<#
On-demand HELP runner with:
- rate limit (default 60s)
- lock (no parallel runs)
- Telegram message via clawdbot
Uses scripts/e2e_always_on_config.json for Telegram target.
Artifacts:
  scripts/_artifacts/help_state.json
  scripts/_artifacts/help.lock
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

function Tg([string]$channel, [string]$target, [string]$text) {
  & clawdbot message send --channel $channel --target $target --message $text | Out-Null
}

$cfgPath = Join-Path $PSScriptRoot 'e2e_always_on_config.json'
$artDir = Join-Path $PSScriptRoot '_artifacts'
$statePath = Join-Path $artDir 'help_state.json'
$lockPath = Join-Path $artDir 'help.lock'

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
  $state = Load-JsonOrDefault $statePath ([pscustomobject]@{ last_run_unix = 0 })
  $nowUnix = [int][DateTimeOffset]::Now.ToUnixTimeSeconds()
  $elapsed = $nowUnix - [int]$state.last_run_unix
  if ($elapsed -lt $RateLimitSeconds) {
    $wait = $RateLimitSeconds - $elapsed
    Tg $channel $target ("HELP rate-limited; try again in {0}s" -f $wait)
    exit 0
  }

  $state.last_run_unix = $nowUnix
  Save-Json $statePath $state

  $msg = @(
    "ClowBot commands:",
    "- status  → health + deps + last smoke/e2e",
    "- smoke   → quick workflow run",
    "- e2e     → full end-to-end run",
    "- help/?  → this menu"
  ) -join "`n"

  Tg $channel $target $msg
  exit 0
} finally {
  Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
}
