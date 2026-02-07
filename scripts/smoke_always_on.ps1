$ErrorActionPreference = 'Stop'

try {
  [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
  $OutputEncoding = [System.Text.UTF8Encoding]::new($false)
} catch {}

$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$cfgPath = Join-Path $PSScriptRoot 'e2e_always_on_config.json'
$artDir = Join-Path $PSScriptRoot '_artifacts'
$lastJson = Join-Path $artDir 'smoke_last.json'

if (-not (Test-Path -LiteralPath $cfgPath)) {
  throw "Missing config: $cfgPath (copy from e2e_always_on_config.example.json)"
}
$cfg = Get-Content -Raw -LiteralPath $cfgPath | ConvertFrom-Json

Push-Location $repo
try {
  $smoke = Join-Path $repo 'scripts\smoke.ps1'
  $null = & powershell -NoProfile -ExecutionPolicy Bypass -File $smoke

  if (-not (Test-Path -LiteralPath $lastJson)) {
    throw "smoke_last.json missing"
  }

  $j = Get-Content -Raw -LiteralPath $lastJson | ConvertFrom-Json
  if ($j.ok -eq $true) { exit 0 }

  $t = (Get-Date).ToString('s')
  $msg = "SMOKE FAILED; time=$t; ok=$($j.ok); duration_ms=$($j.duration_ms); health_ok=$($j.health.ok); deps=$($j.health.deps.postgres),$($j.health.deps.redis),$($j.health.deps.qdrant),$($j.health.deps.minio); wf=$($j.workflow.wf_id); status=$($j.workflow.final_status)/$($j.workflow.final_state); fail_log=$($j.fail_log); error=$($j.error)"
  & clawdbot message send --channel $cfg.TelegramChannel --target $cfg.TelegramTarget --message $msg | Out-Null
  exit 1
} finally {
  Pop-Location -ErrorAction SilentlyContinue
}
