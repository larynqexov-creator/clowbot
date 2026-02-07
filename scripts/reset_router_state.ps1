$ErrorActionPreference='Stop'
try{[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);$OutputEncoding=[Text.UTF8Encoding]::new($false)}catch{}
$p='C:\Users\maste\clawd\clowbot\scripts\_artifacts\telegram_router_state.json'
if (Test-Path -LiteralPath $p) {
  $j = Get-Content -Raw -LiteralPath $p | ConvertFrom-Json
  $j.last_run_unix = 0
  ($j | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath $p -Encoding UTF8
} else {
  New-Item -ItemType Directory -Path (Split-Path -Parent $p) -Force | Out-Null
  '{"last_update_id":0,"last_run_unix":0}' | Set-Content -LiteralPath $p -Encoding UTF8
}
Write-Output 'state reset'
