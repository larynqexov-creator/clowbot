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
  throw "Missing config: $cfgPath (copy from e2e_always_on_config.example.json)"
}

$cfg = Get-Content -Raw -LiteralPath $cfgPath | ConvertFrom-Json
$timeout = if ($cfg.TimeoutSeconds) { [int]$cfg.TimeoutSeconds } else { 900 }

Push-Location $repo
try {
  # Run E2E (this writes scripts/_artifacts/e2e_last.json)
  $e2e = Join-Path $repo 'scripts\e2e.ps1'
  $proc = Start-Process -FilePath 'powershell' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',$e2e) -NoNewWindow -PassThru -Wait
  $exit = $proc.ExitCode

  if (-not (Test-Path -LiteralPath $lastJson)) {
    throw "e2e_last.json missing after run"
  }

  $j = Get-Content -Raw -LiteralPath $lastJson | ConvertFrom-Json

  if ($j.ok -eq $true -and $exit -eq 0) {
    exit 0
  }

  # Failure → send Telegram alert
  $t = (Get-Date).ToString('s')
  $msg = "E2E FAILED; time=$t; ok=$($j.ok); duration_ms=$($j.duration_ms); health_ok=$($j.health.ok); deps=$($j.health.deps.postgres),$($j.health.deps.redis),$($j.health.deps.qdrant),$($j.health.deps.minio); wf=$($j.workflow.wf_id); status=$($j.workflow.final_status)/$($j.workflow.final_state); fail_log=$($j.fail_log); error=$($j.error)"

  & clawdbot message send --channel $cfg.TelegramChannel --target $cfg.TelegramTarget --message $msg | Out-Null
  exit 1
} finally {
  Pop-Location -ErrorAction SilentlyContinue
}
