$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$cfgPath = Join-Path $PSScriptRoot 'always_on_config.json'
$cfgExample = Join-Path $PSScriptRoot 'always_on_config.example.json'

if (-not (Test-Path -LiteralPath $cfgPath)) {
  Copy-Item -LiteralPath $cfgExample -Destination $cfgPath -Force
}

$cfg = Get-Content -Raw -LiteralPath $cfgPath | ConvertFrom-Json
$cfg.TelegramTarget = '95576236'
$cfg.TelegramChannel = 'telegram'
$cfg.HttpTimeoutMs = 1500
$cfg.FailuresBeforeRestart = 3

($cfg | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $cfgPath -Encoding UTF8

# Ping
clawdbot message send --channel telegram --target $cfg.TelegramTarget --message "watchdog test ping" | Out-Null

# Tighten task settings (may require elevation)
try {
  $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
  Set-ScheduledTask -TaskName 'Clawdbot Gateway' -Settings $settings | Out-Null
  Set-ScheduledTask -TaskName 'Clawdbot Gateway Watchdog' -Settings $settings | Out-Null
  Write-Output 'Task settings updated'
} catch {
  Write-Output ("Task settings update skipped (no admin?): {0}" -f $_.Exception.Message)
}

# Stop gateway to simulate failure
try { Stop-ScheduledTask -TaskName 'Clawdbot Gateway' -ErrorAction SilentlyContinue | Out-Null } catch {}

Start-Sleep -Seconds 2

# Run watchdog 3 times quickly (uses state file + lock)
for ($i=1; $i -le 3; $i++) {
  Start-ScheduledTask -TaskName 'Clawdbot Gateway Watchdog' | Out-Null
  Start-Sleep -Seconds 2
}

# Wait for restart to settle
Start-Sleep -Seconds 3

$health = clawdbot health --json --timeout 2000 | ConvertFrom-Json
if (-not $health.ok) {
  throw "Health not ok after restart"
}

# Trigger OK-again notification if needed
Start-ScheduledTask -TaskName 'Clawdbot Gateway Watchdog' | Out-Null

Write-Output 'E2E OK'
Write-Output "watchdog log: $PSScriptRoot\logs\watchdog.log"
