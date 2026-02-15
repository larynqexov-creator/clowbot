param(
  [ValidateSet('auto','compose','ports','names')]
  [string]$Mode = 'auto',

  [int[]]$Ports = @(8000, 9000, 9001, 6379, 6333),

  # Process names are best-effort. On Windows, uvicorn/celery often run as python.exe.
  [string[]]$ProcessNames = @('uvicorn','celery','python','node'),

  [switch]$Force
)

$ErrorActionPreference = 'Stop'

function Write-Info($msg) { Write-Host "[stop_stack] $msg" }

function Test-DockerComposeAvailable {
  try {
    $null = & docker compose version 2>$null
    return $LASTEXITCODE -eq 0
  } catch { return $false }
}

function Stop-DockerCompose {
  Write-Info "Stopping docker compose stack..."
  try {
    & docker compose down
    if ($LASTEXITCODE -ne 0) {
      Write-Info "docker compose down exited with code $LASTEXITCODE"
      return $false
    }
    return $true
  } catch {
    Write-Info "docker compose down failed: $($_.Exception.Message)"
    return $false
  }
}

function Get-ListeningPids([int]$port) {
  try {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if (-not $conns) { return @() }
    return @($conns | Select-Object -ExpandProperty OwningProcess | Sort-Object -Unique)
  } catch {
    return @()
  }
}

function Stop-Pid([int]$pid, [string]$reason) {
  if (-not $pid) { return }
  $p = $null
  try { $p = Get-Process -Id $pid -ErrorAction SilentlyContinue } catch { $p = $null }

  if (-not $p) {
    Write-Info "PID $pid ($reason): process not found"
    return
  }

  $desc = "$($p.ProcessName) pid=$pid"
  Write-Info "Stopping $desc ($reason)"

  if ($Force) {
    Stop-Process -Id $pid -Force -WhatIf:$WhatIfPreference
  } else {
    Stop-Process -Id $pid -WhatIf:$WhatIfPreference
  }
}

function Stop-ByPorts {
  Write-Info "Stopping processes by listening ports: $($Ports -join ', ')"
  $seen = New-Object 'System.Collections.Generic.HashSet[int]'
  foreach ($port in $Ports) {
    foreach ($pid in (Get-ListeningPids $port)) {
      if ($seen.Add([int]$pid)) {
        Stop-Pid -pid $pid -reason "port:$port"
      } else {
        Write-Info "PID $pid already handled (also listening on port $port)"
      }
    }
  }
}

function Stop-ByNames {
  Write-Info "Stopping processes by names (best-effort): $($ProcessNames -join ', ')"
  foreach ($name in $ProcessNames) {
    $procs = @(Get-Process -Name $name -ErrorAction SilentlyContinue)
    foreach ($p in $procs) {
      # Be conservative: for python/node, only stop if it is listening on one of the target ports.
      if ($p.ProcessName -in @('python','node')) {
        $kill = $false
        foreach ($port in $Ports) {
          $pids = Get-ListeningPids $port
          if ($pids -contains $p.Id) { $kill = $true; break }
        }
        if (-not $kill) {
          Write-Info "Skip $($p.ProcessName) pid=$($p.Id): not listening on target ports"
          continue
        }
      }

      Stop-Pid -pid $p.Id -reason "name:$name"
    }
  }
}

function Stop-Auto {
  if (Test-DockerComposeAvailable) {
    # Prefer compose if there is an active stack.
    try {
      $ps = & docker compose ps --status running 2>$null
      if ($LASTEXITCODE -eq 0 -and $ps -match '\S') {
        $ok = Stop-DockerCompose
        if ($ok) { return }
      }
    } catch {
      # fall through
    }
  }

  # Fall back to port-based stop.
  Stop-ByPorts
}

Write-Info "Mode=$Mode Ports=$($Ports -join ',') Force=$Force WhatIf=$WhatIfPreference"

switch ($Mode) {
  'compose' { [void](Stop-DockerCompose) }
  'ports'   { Stop-ByPorts }
  'names'   { Stop-ByNames }
  'auto'    { Stop-Auto }
  default   { throw "Unknown Mode=$Mode" }
}

Write-Info "Done."
