param(
  [ValidateSet('auto','compose')]
  [string]$Mode = 'auto',

  [switch]$Build
)

$ErrorActionPreference = 'Stop'

function Write-Info($msg) { Write-Host "[restart_stack] $msg" }

function Test-DockerComposeAvailable {
  try {
    $null = & docker compose version 2>$null
    return $LASTEXITCODE -eq 0
  } catch { return $false }
}

function Start-DockerCompose {
  if (-not (Test-DockerComposeAvailable)) {
    throw "docker compose not available"
  }

  Write-Info "Starting docker compose stack..."
  if ($Build) {
    & docker compose up -d --build
  } else {
    & docker compose up -d
  }

  if ($LASTEXITCODE -ne 0) {
    throw "docker compose up failed with code $LASTEXITCODE"
  }

  & docker compose ps
}

Write-Info "Mode=$Mode Build=$Build WhatIf=$WhatIfPreference"

switch ($Mode) {
  'compose' { Start-DockerCompose }
  'auto'    { Start-DockerCompose }
  default   { throw "Unknown Mode=$Mode" }
}
