param(
  [string]$ConfigPath = "$PSScriptRoot\always_on_config.json",
  [string]$GatewayHost = '127.0.0.1',
  [int]$GatewayPort = 18789,
  [int]$FailuresBeforeRestart = 3,
  [int]$HttpTimeoutMs = 1500,
  [string]$HealthUrl = 'http://127.0.0.1:18789/health',
  [string]$TelegramTarget = '',
  [string]$TelegramChannel = 'telegram',
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
    if ($cfg.HttpTimeoutMs) { $HttpTimeoutMs = [int]$cfg.HttpTimeoutMs }
    if ($cfg.HealthUrl) { $HealthUrl = [string]$cfg.HealthUrl }
    if ($cfg.TelegramTarget) { $TelegramTarget = [string]$cfg.TelegramTarget }
    if ($cfg.TelegramChannel) { $TelegramChannel = [string]$cfg.TelegramChannel }
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

function Get-GatewayHealthJson($timeoutMs) {
  try {
    $raw = & clawdbot health --json --timeout $timeoutMs 2>$null
    if (-not $raw) { return $null }
    return ($raw | ConvertFrom-Json)
  } catch {
    return $null
  }
}

function Get-GatewayPid() {
  try {
    $raw = & clawdbot gateway status --json 2>$null
    if (-not $raw) { return $null }
    $j = $raw | ConvertFrom-Json
    if ($j.port -and $j.port.listeners -and $j.port.listeners.Count -gt 0) {
      return [int]$j.port.listeners[0].pid
    }
    return $null
  } catch {
    return $null
  }
}

function Test-TelegramConnectedFromHealth($health) {
  try {
    if (-not $health) { return $false }
    if (-not $health.channels) { return $false }
    $tg = $health.channels.telegram
    if (-not $tg) { return $false }
    if ($tg.probe -and $tg.probe.ok -eq $true) { return $true }
    return $false
  } catch {
    return $false
  }
}

function Send-Telegram($text) {
  if (-not $TelegramTarget) { return }
  try {
    & clawdbot message send --channel $TelegramChannel --target $TelegramTarget --message $text | Out-Null
  } catch {
    # don't crash watchdog due to notify errors
    Log "Telegram notify failed: $($_.Exception.Message)"
  }
}

function Read-State() {
  if (Test-Path -LiteralPath $StatePath) {
    try { return (Get-Content -Raw -LiteralPath $StatePath | ConvertFrom-Json) } catch { }
  }
  return [pscustomobject]@{ failures = 0; lastRestart = $null; lastOk = $null }
}

function Write-State($st) {
  ($st | ConvertTo-Json -Depth 4) | Out-File -LiteralPath $StatePath -Encoding utf8
}

function Restart-Gateway([string]$reason) {
  $beforePid = Get-GatewayPid
  Log "Restart requested (reason=$reason, pid_before=$beforePid)"
  Send-Telegram ("gateway restarting; reason={0}; time={1}; pid_before={2}" -f $reason, (Get-Date).ToString('s'), $beforePid)

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
    Log "clawdbot restart failed, trying task restart: $($_.Exception.Message)"
    try {
      Stop-ScheduledTask -TaskName 'Clawdbot Gateway' -ErrorAction SilentlyContinue | Out-Null
    } catch { }
    try {
      Start-ScheduledTask -TaskName 'Clawdbot Gateway' -ErrorAction SilentlyContinue | Out-Null
      Log "Triggered Start-ScheduledTask: Clawdbot Gateway"
    } catch {
      # final fallback
      schtasks /Run /TN "Clawdbot Gateway" | Out-Null
      Log "Triggered schtasks run: Clawdbot Gateway"
    }
  }

  Start-Sleep -Seconds 2
  $afterPid = Get-GatewayPid
  Log "Restart complete (pid_after=$afterPid)"
  Send-Telegram ("gateway restarted; reason={0}; time={1}; pid_after={2}" -f $reason, (Get-Date).ToString('s'), $afterPid)
}

With-Lock $LockPath {
  $st = Read-State

  $tcpOk = Test-GatewayTcp $GatewayHost $GatewayPort
  $health = $null
  $healthOk = $false
  $tgOk = $false

  if ($tcpOk) {
    $health = Get-GatewayHealthJson $HttpTimeoutMs
    if ($health -and $health.ok -eq $true) { $healthOk = $true }
    $tgOk = Test-TelegramConnectedFromHealth $health
  }

  $ok = ($tcpOk -and $healthOk -and $tgOk)

  if ($ok) {
    if ($st.failures -ne 0) {
      Log "Gateway OK again (reset failures from $($st.failures) -> 0)"
      Send-Telegram ("gateway ok again; time={0}" -f (Get-Date).ToString('s'))
    }
    $st.failures = 0
    $st.lastOk = (Get-Date).ToString('o')
    Write-State $st
    return
  }

  $st.failures = [int]$st.failures + 1
  Log "Health check failed (tcp=$tcpOk http=$httpOk tg=$tgOk) failures=$($st.failures)/$FailuresBeforeRestart"
  Write-State $st

  if ($st.failures -ge $FailuresBeforeRestart) {
    # cool-down: avoid restart storms
    if ($st.lastRestart) {
      try {
        $lr = [DateTime]::Parse($st.lastRestart)
        if ((Get-Date) -lt $lr.AddSeconds(60)) {
          Log "Restart suppressed (cooldown)"
          return
        }
      } catch { }
    }

    Restart-Gateway "health_timeout"
    $st.failures = 0
    $st.lastRestart = (Get-Date).ToString('o')
    Write-State $st
  }
}
