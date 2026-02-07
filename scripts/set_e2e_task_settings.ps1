$ErrorActionPreference='Stop'
$name='Clowbot E2E Nightly'
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Set-ScheduledTask -TaskName $name -Settings $settings | Out-Null
Write-Output 'settings ok'
