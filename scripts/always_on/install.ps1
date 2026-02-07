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
$configPath = Join-Path $PSScriptRoot 'always_on_config.json'

# Prefer Windows Service only if admin. Otherwise fall back to Scheduled Task.
if ($Mode -eq 'auto') {
  if (Is-Admin) { $Mode = 'service' } else { $Mode = 'task' }
}

Write-Output "Installing always-on gateway in mode: $Mode"

# Write config (used by runner/watchdog so task command lines stay short)
$cfg = [pscustomobject]@{
  Mode = $Mode
  ServiceName = $ServiceName
  TaskName = $TaskName
  WatchdogTaskName = $WatchdogTaskName
  LogsDir = $LogsDir
  GatewayHost = $GatewayHost
  GatewayPort = $GatewayPort
  FailuresBeforeRestart = $FailuresBeforeRestart
}
($cfg | ConvertTo-Json -Depth 4) | Out-File -LiteralPath $configPath -Encoding utf8

if ($Mode -eq 'service') {
  if (-not (Is-Admin)) {
    Write-Output "Not running as admin, cannot create service. Falling back to task."
    $Mode = 'task'
  }
}

if ($Mode -eq 'service') {
  # Create/update service
  $binPath = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File $runner"

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
  $wdCmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File $watchdog"
  schtasks /Create /F /TN "$WatchdogTaskName" /SC MINUTE /MO 1 /RL HIGHEST /TR "$wdCmd" | Out-Null

  Write-Output "Done."
  exit 0
}

# TASK MODE
Write-Output "Installing Scheduled Tasks under current user (no admin required)"

# Use schtasks.exe for compatibility across Windows builds.
# NOTE: Creating tasks may require elevation depending on local policy.

$ps = "powershell.exe"
$gwCmd = "$ps -NoProfile -ExecutionPolicy Bypass -File `"$runner`""
$wdCmd = "$ps -NoProfile -ExecutionPolicy Bypass -File `"$watchdog`""

Write-Output "Registering task: $TaskName"
& schtasks.exe @('/Create','/F','/TN', $TaskName, '/SC','ONLOGON','/RL','LIMITED','/TR', $gwCmd) | Out-Null

Write-Output "Registering task: $WatchdogTaskName"
& schtasks.exe @('/Create','/F','/TN', $WatchdogTaskName, '/SC','MINUTE','/MO','1','/RL','LIMITED','/TR', $wdCmd) | Out-Null

# Kick gateway once now
try { schtasks.exe /Run /TN "$TaskName" | Out-Null } catch {}

Write-Output "Done."
Write-Output "Logs: $LogsDir"
