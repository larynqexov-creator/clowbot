param(
  [string]$ConfigPath = "$PSScriptRoot\always_on_config.json",
  [string]$GatewayHost = '127.0.0.1',
  [int]$GatewayPort = 18789,
  [int]$FailuresBeforeRestart = 3,
  [string]$Mode = 'auto', # auto|service|task
  [string]$ServiceName = 'clawdbot-gateway',
  [string]$TaskName = 'Clawdbot Gateway (Always On)',
  [string]$WatchdogTaskName = 'Clawdbot Gateway Watchdog',
  [string]$LogsDir = "$PSScriptRoot\logs",
  [string]$LockPath = "$PSScriptRoot\watchdog.lock",
  [string]$StatePath = "$PSScriptRoot\watchdog-state.json"
)

$ErrorActionPreference = 'Stop'

# Load config if present (keeps schtasks /TR short)
if (Test-Path -LiteralPath $ConfigPath) {
  try {
    $cfg = Get-Content -Raw -LiteralPath $ConfigPath | ConvertFrom-Json
    if ($cfg.GatewayHost) { $GatewayHost = [string]$cfg.GatewayHost }
    if ($cfg.GatewayPort) { $GatewayPort = [int]$cfg.GatewayPort }
    if ($cfg.FailuresBeforeRestart) { $FailuresBeforeRestart = [int]$cfg.FailuresBeforeRestart }
    if ($cfg.Mode) { $Mode = [string]$cfg.Mode }
    if ($cfg.ServiceName) { $ServiceName = [string]$cfg.ServiceName }
    if ($cfg.TaskName) { $TaskName = [string]$cfg.TaskName }
    if ($cfg.WatchdogTaskName) { $WatchdogTaskName = [string]$cfg.WatchdogTaskName }
    if ($cfg.LogsDir) { $LogsDir = [string]$cfg.LogsDir }
  } catch {
    # ignore config parse errors
  }
}

function Ensure-Dir($p) {
  if (-not (Test-Path -LiteralPath $p)) { New-Item -ItemType Directory -Path $p | Out-Null }
}

function Log($msg) {
  Ensure-Dir $LogsDir
  $ts = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
  $line = "$ts [watchdog] $msg"
  $line | Out-File -FilePath (Join-Path $LogsDir 'watchdog.log') -Append -Encoding utf8
}

function With-Lock($path, [scriptblock]$body) {
  Ensure-Dir (Split-Path -Parent $path)
  $fs = $null
  try {
    $fs = [System.IO.File]::Open($path, [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
    & $body
  } catch {
    # If lock is held by another watchdog instance, just exit cleanly.
    if ($_.Exception -and $_.Exception.Message -match 'because it is being used by another process') {
      return
    }
    throw
  } finally {
    if ($fs) { $fs.Dispose() }
  }
}

function Test-GatewayTcp($h, $port) {
  try {
    $client = New-Object System.Net.Sockets.TcpClient
    $iar = $client.BeginConnect($h, $port, $null, $null)
    $ok = $iar.AsyncWaitHandle.WaitOne(800)
    if (-not $ok) { $client.Close(); return $false }
    $client.EndConnect($iar)
    $client.Close()
    return $true
  } catch {
    return $false
  }
}

function Read-State() {
  if (Test-Path -LiteralPath $StatePath) {
    try { return (Get-Content -Raw -LiteralPath $StatePath | ConvertFrom-Json) } catch { }
  }
  return [pscustomobject]@{ failures = 0; lastRestart = $null }
}

function Write-State($st) {
  ($st | ConvertTo-Json -Depth 4) | Out-File -LiteralPath $StatePath -Encoding utf8
}

function Restart-Gateway() {
  Log "Restart requested"

  if ($Mode -eq 'auto') {
    $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($svc) { $Mode = 'service' } else { $Mode = 'task' }
  }

  if ($Mode -eq 'service') {
    $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (-not $svc) { throw "Service not found: $ServiceName" }
    try {
      Restart-Service -Name $ServiceName -Force -ErrorAction Stop
      Log "Service restarted: $ServiceName"
      return
    } catch {
      Log "Service restart failed: $($_.Exception.Message)"
      throw
    }
  }

  # Task mode
  try {
    # Prefer a clean restart via clawdbot CLI if available
    $null = & clawdbot gateway restart 2>&1
    Log "Restarted via: clawdbot gateway restart"
  } catch {
    Log "clawdbot restart failed, trying task kick: $($_.Exception.Message)"
    try {
      schtasks /Run /TN "$TaskName" | Out-Null
      Log "Triggered task run: $TaskName"
    } catch {
      throw
    }
  }
}

With-Lock $LockPath {
  $ok = Test-GatewayTcp $GatewayHost $GatewayPort
  $st = Read-State

  if ($ok) {
    if ($st.failures -ne 0) { Log "Gateway OK (reset failures from $($st.failures) -> 0)" }
    $st.failures = 0
    Write-State $st
    return
  }

  $st.failures = [int]$st.failures + 1
  Log "Gateway NOT responding on $GatewayHost:$GatewayPort (failures=$($st.failures)/$FailuresBeforeRestart)"
  Write-State $st

  if ($st.failures -ge $FailuresBeforeRestart) {
    Restart-Gateway
    $st.failures = 0
    $st.lastRestart = (Get-Date).ToString('o')
    Write-State $st
  }
}
