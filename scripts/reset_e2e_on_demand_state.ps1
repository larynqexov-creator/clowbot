$ErrorActionPreference='Stop'
$p='C:\Users\maste\clawd\clowbot\scripts\_artifacts\e2e_on_demand_state.json'
if (Test-Path -LiteralPath $p) {
  $j = Get-Content -Raw -LiteralPath $p | ConvertFrom-Json
  $j.last_run_unix = 0
  ($j | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath $p -Encoding UTF8
} else {
  New-Item -ItemType Directory -Path (Split-Path -Parent $p) -Force | Out-Null
  '{"last_run_unix":0}' | Set-Content -LiteralPath $p -Encoding UTF8
}
'reset'
