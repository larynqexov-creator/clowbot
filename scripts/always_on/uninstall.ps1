param(
  [string]$ServiceName = 'clawdbot-gateway',
  [string]$TaskName = 'Clawdbot Gateway (Always On)',
  [string]$WatchdogTaskName = 'Clawdbot Gateway Watchdog'
)
$ErrorActionPreference = 'Stop'

Write-Output "Removing Scheduled Tasks (if present)..."
# Prefer schtasks.exe (works even without ScheduledTasks module)
try { schtasks.exe /End /TN "$TaskName" | Out-Null } catch {}
try { schtasks.exe /Delete /TN "$TaskName" /F | Out-Null } catch {}

try { schtasks.exe /End /TN "$WatchdogTaskName" | Out-Null } catch {}
try { schtasks.exe /Delete /TN "$WatchdogTaskName" /F | Out-Null } catch {}

# Backward-compat cleanup (older names)
try { schtasks.exe /End /TN "$TaskName (OnLogon)" | Out-Null } catch {}
try { schtasks.exe /Delete /TN "$TaskName (OnLogon)" /F | Out-Null } catch {}

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
