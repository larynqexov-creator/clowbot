param(
  [ValidateSet('auto','service','task')][string]$Mode = 'auto',
  [string]$ServiceName = 'clawdbot-gateway',
  [string]$TaskName = 'Clawdbot Gateway (Always On)',
  [string]$WatchdogTaskName = 'Clawdbot Gateway Watchdog',
  [string]$LogsDir = "$PSScriptRoot\logs",
  [string]$GatewayHost = '127.0.0.1',
  [int]$GatewayPort = 18789,
  [int]$FailuresBeforeRestart = 3
)

$ErrorActionPreference = 'Stop'

function Ensure-Dir($p) {
  if (-not (Test-Path -LiteralPath $p)) { New-Item -ItemType Directory -Path $p | Out-Null }
}

function Is-Admin() {
  $id = [Security.Principal.WindowsIdentity]::GetCurrent()
  $p = New-Object Security.Principal.WindowsPrincipal($id)
  return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

Ensure-Dir $LogsDir

$runner = Join-Path $PSScriptRoot 'runner.ps1'
$watchdog = Join-Path $PSScriptRoot 'watchdog.ps1'

# Prefer Windows Service only if admin. Otherwise fall back to Scheduled Task.
if ($Mode -eq 'auto') {
  if (Is-Admin) { $Mode = 'service' } else { $Mode = 'task' }
}

Write-Output "Installing always-on gateway in mode: $Mode"

if ($Mode -eq 'service') {
  if (-not (Is-Admin)) {
    Write-Output "Not running as admin, cannot create service. Falling back to task."
    $Mode = 'task'
  }
}

if ($Mode -eq 'service') {
  # Create/update service
  $binPath = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$runner`" -LogsDir `"$LogsDir`""

  $existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
  if ($existing) {
    Write-Output "Service exists, updating binPath and restarting: $ServiceName"
    sc.exe config $ServiceName binPath= "$binPath" start= auto | Out-Null
  } else {
    Write-Output "Creating service: $ServiceName"
    sc.exe create $ServiceName binPath= "$binPath" start= auto DisplayName= "Clawdbot Gateway" | Out-Null
  }

  # Recovery: restart after 5 seconds, 3 times, reset after 1 day
  sc.exe failure $ServiceName reset= 86400 actions= restart/5000/restart/5000/restart/5000 | Out-Null

  # Start service
  try { Start-Service -Name $ServiceName -ErrorAction Stop } catch { Restart-Service -Name $ServiceName -Force }
  Write-Output "Service installed and started: $ServiceName"

  # Install watchdog as Scheduled Task (works even if gateway is a service)
  Write-Output "Installing watchdog task (runs every minute): $WatchdogTaskName"
  $wdCmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$watchdog`" -Mode service -ServiceName `"$ServiceName`" -GatewayHost `"$GatewayHost`" -GatewayPort $GatewayPort -FailuresBeforeRestart $FailuresBeforeRestart -LogsDir `"$LogsDir`""
  schtasks /Create /F /TN "$WatchdogTaskName" /SC MINUTE /MO 1 /RL HIGHEST /TR "$wdCmd" | Out-Null

  Write-Output "Done."
  exit 0
}

# TASK MODE
Write-Output "Installing gateway task (at startup + on logon): $TaskName"

$gwCmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$runner`" -LogsDir `"$LogsDir`""

# Create task that runs at startup
schtasks /Create /F /TN "$TaskName" /SC ONSTART /RL HIGHEST /TR "$gwCmd" | Out-Null
# Also create logon trigger by duplicating task name with suffix (simple + reliable)
$taskLogon = "$TaskName (OnLogon)"
schtasks /Create /F /TN "$taskLogon" /SC ONLOGON /RL HIGHEST /TR "$gwCmd" | Out-Null

Write-Output "Installing watchdog task (runs every minute): $WatchdogTaskName"
$wdCmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$watchdog`" -Mode task -TaskName `"$TaskName`" -GatewayHost `"$GatewayHost`" -GatewayPort $GatewayPort -FailuresBeforeRestart $FailuresBeforeRestart -LogsDir `"$LogsDir`""
schtasks /Create /F /TN "$WatchdogTaskName" /SC MINUTE /MO 1 /RL HIGHEST /TR "$wdCmd" | Out-Null

# Kick it once now
try { schtasks /Run /TN "$TaskName" | Out-Null } catch {}

Write-Output "Done."
Write-Output "Logs: $LogsDir"
