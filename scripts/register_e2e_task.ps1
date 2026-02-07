$ErrorActionPreference = 'Stop'

$name = 'Clowbot E2E Nightly'
$script = 'C:\Users\maste\clawd\clowbot\scripts\e2e_always_on.ps1'

$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`""

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1)
$trigger.RepetitionInterval = (New-TimeSpan -Hours 6)
$trigger.RepetitionDuration = ([TimeSpan]::MaxValue)

$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null

Write-Output "registered: \\$name"
