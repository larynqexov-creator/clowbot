$ErrorActionPreference = 'Stop'

$logDir = Join-Path $PSScriptRoot 'logs'
$log = Join-Path $logDir 'watchdog.log'

if (-not (Test-Path -LiteralPath $logDir)) {
  New-Item -ItemType Directory -Path $logDir | Out-Null
}

$maxBytes = 1MB
$len = 0
if (Test-Path -LiteralPath $log) {
  $len = (Get-Item -LiteralPath $log).Length
}

if ($len -gt $maxBytes) {
  $ts = (Get-Date).ToString('yyyyMMdd-HHmmss')
  $rotated = Join-Path $logDir ("watchdog.$ts.log")
  Move-Item -LiteralPath $log -Destination $rotated -Force
  New-Item -ItemType File -Path $log -Force | Out-Null
  $line = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') + " [watchdog] watchdog log rotated at $ts (prev_bytes=$len)"
  Add-Content -LiteralPath $log -Value $line -Encoding UTF8
  Write-Output "rotated=$rotated"
} else {
  Write-Output "no-rotate bytes=$len"
}
