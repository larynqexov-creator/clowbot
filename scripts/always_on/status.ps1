param(
  [string]$GatewayHost = '127.0.0.1',
  [int]$GatewayPort = 18789,
  [string]$ServiceName = 'clawdbot-gateway',
  [string]$TaskName = 'Clawdbot Gateway (Always On)',
  [string]$WatchdogTaskName = 'Clawdbot Gateway Watchdog',
  [string]$LogsDir = "$PSScriptRoot\logs"
)
$ErrorActionPreference = 'Stop'

function Test-Tcp($host, $port) {
  try {
    $client = New-Object System.Net.Sockets.TcpClient
    $iar = $client.BeginConnect($host, $port, $null, $null)
    $ok = $iar.AsyncWaitHandle.WaitOne(800)
    if (-not $ok) { $client.Close(); return $false }
    $client.EndConnect($iar)
    $client.Close()
    return $true
  } catch { return $false }
}

Write-Output "== Gateway connectivity =="
$tcp = Test-Tcp $GatewayHost $GatewayPort
Write-Output ("TCP {0}:{1} => {2}" -f $GatewayHost, $GatewayPort, $tcp)

Write-Output "\n== clawdbot gateway status =="
try { clawdbot gateway status } catch { Write-Output ("clawdbot status failed: {0}" -f $_.Exception.Message) }

Write-Output "\n== Windows Service =="
$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($svc) {
  $svc | Format-Table -AutoSize
} else {
  Write-Output "Service not installed: $ServiceName"
}

Write-Output "\n== Scheduled Tasks =="
try { schtasks /Query /TN "$TaskName" /FO LIST /V } catch { Write-Output "Task not found: $TaskName" }
try { schtasks /Query /TN "$WatchdogTaskName" /FO LIST /V } catch { Write-Output "Task not found: $WatchdogTaskName" }

Write-Output "\n== Recent logs =="
$gwLog = Join-Path $LogsDir 'gateway.log'
$wdLog = Join-Path $LogsDir 'watchdog.log'
if (Test-Path $gwLog) {
  Write-Output "--- gateway.log (tail 50) ---"
  Get-Content -Tail 50 $gwLog
} else {
  Write-Output "No gateway.log yet: $gwLog"
}
if (Test-Path $wdLog) {
  Write-Output "--- watchdog.log (tail 50) ---"
  Get-Content -Tail 50 $wdLog
} else {
  Write-Output "No watchdog.log yet: $wdLog"
}
