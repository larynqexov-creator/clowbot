param(
  [string]$ServiceName = 'clawdbot-gateway',
  [string]$TaskName = 'Clawdbot Gateway (Always On)',
  [string]$WatchdogTaskName = 'Clawdbot Gateway Watchdog'
)
$ErrorActionPreference = 'Stop'

Write-Output "Removing Scheduled Tasks (if present)..."
try { schtasks /End /TN "$TaskName" | Out-Null } catch {}
try { schtasks /Delete /TN "$TaskName" /F | Out-Null } catch {}
try { schtasks /End /TN "$WatchdogTaskName" | Out-Null } catch {}
try { schtasks /Delete /TN "$WatchdogTaskName" /F | Out-Null } catch {}

Write-Output "Removing Windows Service (if present)..."
$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($svc) {
  try { Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue } catch {}
  sc.exe delete $ServiceName | Out-Null
  Write-Output "Service deleted: $ServiceName"
} else {
  Write-Output "Service not installed: $ServiceName"
}

Write-Output "Done."
