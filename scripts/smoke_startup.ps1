<#
Smoke at startup.
- Waits for Docker to be available (10 tries x 10s). If not available, exit 0 (no alert).
- Then runs scripts/smoke_always_on.cmd (which handles alert-on-fail).
#>

$ErrorActionPreference='Stop'

try {
  $utf8 = [System.Text.UTF8Encoding]::new($false)
  [Console]::OutputEncoding = $utf8
  [Console]::InputEncoding = $utf8
  $OutputEncoding = $utf8
} catch {}

$tries = 10
for ($i=1; $i -le $tries; $i++) {
  try {
    docker version | Out-Null
    break
  } catch {
    if ($i -eq $tries) {
      exit 0
    }
    Start-Sleep -Seconds 10
  }
}

& "C:\Users\maste\clawd\clowbot\scripts\smoke_always_on.cmd"
exit $LASTEXITCODE
