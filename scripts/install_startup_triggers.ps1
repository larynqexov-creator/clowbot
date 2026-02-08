<#
Install startup-trigger scheduled tasks (safe, no downtime).
Creates/updates:
  - \Clawdbot Gateway Startup (ONSTART + 60s delay) -> C:\Users\maste\.clawdbot\gateway.cmd
  - \Clowbot Smoke Startup (ONSTART + 180s delay) -> C:\Users\maste\clawd\clowbot\scripts\smoke_startup.cmd
Does not modify existing schedule tasks.
#>

$ErrorActionPreference='Stop'

function Create-Or-UpdateTask(
  [string]$name,
  [string]$tr
) {
  # No /DELAY: some Windows builds reject /DELAY for ONSTART. We implement delay in wrapper .cmd via timeout.
  # Avoid quoting issues by invoking schtasks.exe directly with a single argument string.
  $arg = "/Create /TN `"$name`" /SC ONSTART /TR `"$tr`" /F /RL LIMITED"
  $p = Start-Process -FilePath 'schtasks.exe' -ArgumentList $arg -NoNewWindow -Wait -PassThru
  if ($p.ExitCode -ne 0) { throw "schtasks create failed ($name) code=$($p.ExitCode)" }
}

# Tasks
Create-Or-UpdateTask -name 'Clawdbot Gateway Startup' -tr 'C:\Users\maste\clawd\clowbot\scripts\gateway_startup.log.cmd'
Create-Or-UpdateTask -name 'Clowbot Smoke Startup' -tr 'C:\Users\maste\clawd\clowbot\scripts\smoke_startup_wrapper.cmd'

# Settings hardening (IgnoreNew, StartWhenAvailable, restart on failure)
try {
  $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
  Set-ScheduledTask -TaskName 'Clawdbot Gateway Startup' -Settings $settings | Out-Null
  Set-ScheduledTask -TaskName 'Clowbot Smoke Startup' -Settings $settings | Out-Null
} catch {
  # may require elevation; tasks still exist.
}

Write-Output 'startup triggers installed'
