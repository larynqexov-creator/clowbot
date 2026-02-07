# Backwards-compat wrapper: on-demand E2E with start/finish + rate-limit + lock
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'e2e_on_demand.ps1')
