$ErrorActionPreference = 'Stop'

try {
  [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
  $OutputEncoding = [System.Text.UTF8Encoding]::new($false)
} catch {}

$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$cfgPath = Join-Path $PSScriptRoot 'e2e_always_on_config.json'
$artDir = Join-Path $PSScriptRoot '_artifacts'
$lastJson = Join-Path $artDir 'e2e_last.json'

if (-not (Test-Path -LiteralPath $cfgPath)) {
  throw "Missing config: $cfgPath"
}
$cfg = Get-Content -Raw -LiteralPath $cfgPath | ConvertFrom-Json

Push-Location $repo
try {
  $e2e = Join-Path $repo 'scripts\e2e.ps1'
  $null = & powershell -NoProfile -ExecutionPolicy Bypass -File $e2e

  if (-not (Test-Path -LiteralPath $lastJson)) {
    throw "e2e_last.json missing"
  }
  $j = Get-Content -Raw -LiteralPath $lastJson | ConvertFrom-Json

  $t = (Get-Date).ToString('s')
  $msg = "E2E result; time=$t; ok=$($j.ok); duration_ms=$($j.duration_ms); health_ok=$($j.health.ok); wf=$($j.workflow.wf_id); status=$($j.workflow.final_status)/$($j.workflow.final_state); grants_count=$($j.workflow.grants_count)"
  & clawdbot message send --channel $cfg.TelegramChannel --target $cfg.TelegramTarget --message $msg | Out-Null
} finally {
  Pop-Location -ErrorAction SilentlyContinue
}
