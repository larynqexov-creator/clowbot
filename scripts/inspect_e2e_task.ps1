$ErrorActionPreference='Stop'
$t = Get-ScheduledTask -TaskName 'Clowbot E2E Nightly'
$s = $t.Settings
Write-Output "== Clowbot E2E Nightly =="
Write-Output ("StartWhenAvailable={0}" -f $s.StartWhenAvailable)
Write-Output ("MultipleInstances={0}" -f $s.MultipleInstances)
Write-Output ("RestartCount={0}" -f $s.RestartCount)
Write-Output ("RestartInterval={0}" -f $s.RestartInterval)
