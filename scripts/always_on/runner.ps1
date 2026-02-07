param(
  [string]$LogsDir = "$PSScriptRoot\logs"
)

$ErrorActionPreference = 'Stop'

function Ensure-Dir($p) {
  if (-not (Test-Path -LiteralPath $p)) { New-Item -ItemType Directory -Path $p | Out-Null }
}

Ensure-Dir $LogsDir
$logFile = Join-Path $LogsDir 'gateway.log'

function Log($msg) {
  $ts = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
  "$ts [runner] $msg" | Out-File -FilePath $logFile -Append -Encoding utf8
}

# Keep a single long-running process in this context.
# If gateway exits, wait 5s and start again.
while ($true) {
  try {
    Log "Starting: clawdbot gateway start"

    $p = Start-Process -FilePath "clawdbot" -ArgumentList @("gateway","start") -NoNewWindow -PassThru -RedirectStandardOutput (Join-Path $LogsDir 'gateway-stdout.log') -RedirectStandardError (Join-Path $LogsDir 'gateway-stderr.log')
    $p.WaitForExit()

    Log "Gateway process exited with code $($p.ExitCode). Restarting in 5s."
  } catch {
    Log "Runner error: $($_.Exception.Message). Restarting in 5s."
  }

  Start-Sleep -Seconds 5
}
