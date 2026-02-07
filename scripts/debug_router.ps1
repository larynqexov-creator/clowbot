$ErrorActionPreference='Stop'
try{[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);$OutputEncoding=[Text.UTF8Encoding]::new($false)}catch{}
$cfgPath = 'C:\Users\maste\clawd\clowbot\scripts\e2e_always_on_config.json'
$cfg = Get-Content -Raw -LiteralPath $cfgPath | ConvertFrom-Json
$target = [string]$cfg.TelegramTarget
$clawCfgPath = Join-Path $env:USERPROFILE '.clawdbot\clawdbot.json'
$clawCfg = Get-Content -Raw -LiteralPath $clawCfgPath | ConvertFrom-Json
$token = $clawCfg.channels.telegram.botToken
$uri1 = "https://api.telegram.org/bot$token/getWebhookInfo"
$uri2 = "https://api.telegram.org/bot$token/getUpdates?offset=0&limit=20&timeout=0"
$webhook = Invoke-RestMethod -Method Get -Uri $uri1 -TimeoutSec 15
$updates = Invoke-RestMethod -Method Get -Uri $uri2 -TimeoutSec 15
[pscustomobject]@{ webhook=$webhook; updates=$updates } | ConvertTo-Json -Depth 10
