$ErrorActionPreference = 'Stop'

function Show-Task($name) {
  $t = Get-ScheduledTask -TaskName $name
  $s = $t.Settings
  Write-Output "== $name =="
  Write-Output ("StartWhenAvailable={0}" -f $s.StartWhenAvailable)
  Write-Output ("MultipleInstances={0}" -f $s.MultipleInstances)
  Write-Output ("RestartCount={0}" -f $s.RestartCount)
  Write-Output ("RestartInterval={0}" -f $s.RestartInterval)
  Write-Output ("ExecutionTimeLimit={0}" -f $s.ExecutionTimeLimit)
  Write-Output ''
}

Show-Task 'Clawdbot Gateway'
Show-Task 'Clawdbot Gateway Watchdog'
