<#
On-demand STATUS runner with:
- rate limit (60s)
- lock (no parallel runs)
- busy-check: e2e_on_demand.lock / smoke_on_demand.lock
- Telegram start/finish messages via clawdbot
Uses scripts/e2e_always_on_config.json for Telegram target.
Artifacts:
  scripts/_artifacts/status_state.json
  scripts/_artifacts/status.lock
  scripts/_artifacts/status_fail_*.log
#>

param(
  [int]$RateLimitSeconds = 60
)

$ErrorActionPreference = 'Stop'

try {
  $utf8 = [System.Text.UTF8Encoding]::new($false)
  [Console]::OutputEncoding = $utf8
  [Console]::InputEncoding = $utf8
  $OutputEncoding = $utf8
} catch {}

function Ensure-Dir([string]$p) {
  if (-not (Test-Path -LiteralPath $p)) { New-Item -ItemType Directory -Path $p | Out-Null }
}

function Load-JsonOrDefault([string]$path, $default) {
  try {
    if (Test-Path -LiteralPath $path) {
      return (Get-Content -Raw -LiteralPath $path | ConvertFrom-Json)
    }
  } catch {}
  return $default
}

function Save-Json([string]$path, $obj) {
  $dir = Split-Path -Parent $path
  if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
  ($obj | ConvertTo-Json -Depth 10) | Set-Content -LiteralPath $path -Encoding UTF8
}

function Read-JsonOrNull([string]$p) {
  try {
    if (Test-Path -LiteralPath $p) {
      return (Get-Content -Raw -LiteralPath $p | ConvertFrom-Json)
    }
  } catch {}
  return $null
}

function File-TimeOrNull([string]$p) {
  try {
    if (Test-Path -LiteralPath $p) {
      return (Get-Item -LiteralPath $p).LastWriteTime.ToString('s')
    }
  } catch {}
  return $null
}

function SafePath([string]$p) {
  if (-not $p) { return $null }
  return ([string]$p) -replace '\\','/'
}

function ShortId([string]$s, [int]$n = 8) {
  if (-not $s) { return $null }
  $s = [string]$s
  if ($s.Length -le $n) { return $s }
  return $s.Substring(0, $n)
}

function Summarize-Last($j, [string]$time) {
  if (-not $j) { return 'n/a' }
  $ok = $j.ok
  $wf = $null
  $st = $null
  try { $wf = ShortId ([string]$j.workflow.wf_id) 8 } catch {}
  try { $st = ("{0}/{1}" -f $j.workflow.final_status, $j.workflow.final_state) } catch {}
  if (-not $time) { $time = 'n/a' }
  if (-not $wf) { $wf = 'n/a' }
  if (-not $st) { $st = 'n/a' }
  return ("ok={0} time={1} wf={2} status={3}" -f $ok, $time, $wf, $st)
}

function Tg([string]$channel, [string]$target, [string]$text) {
  & clawdbot message send --channel $channel --target $target --message $text | Out-Null
}

$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$cfgPath = Join-Path $PSScriptRoot 'e2e_always_on_config.json'
$artDir = Join-Path $PSScriptRoot '_artifacts'
$statePath = Join-Path $artDir 'status_state.json'
$lockPath = Join-Path $artDir 'status.lock'
$e2eLock = Join-Path $artDir 'e2e_on_demand.lock'
$smokeLock = Join-Path $artDir 'smoke_on_demand.lock'

Ensure-Dir $artDir

if (-not (Test-Path -LiteralPath $cfgPath)) {
  throw "Missing config: $cfgPath"
}
$cfg = Get-Content -Raw -LiteralPath $cfgPath | ConvertFrom-Json
$channel = [string]$cfg.TelegramChannel
if (-not $channel) { $channel = 'telegram' }
$target = [string]$cfg.TelegramTarget

# lock
try {
  New-Item -ItemType File -Path $lockPath -Force -ErrorAction Stop | Out-Null
} catch {
  exit 0
}

try {
  if (Test-Path -LiteralPath $e2eLock) { Tg $channel $target "STATUS busy: e2e running"; exit 0 }
  if (Test-Path -LiteralPath $smokeLock) { Tg $channel $target "STATUS busy: smoke running"; exit 0 }

  $state = Load-JsonOrDefault $statePath ([pscustomobject]@{ last_run_unix = 0 })
  $nowUnix = [int][DateTimeOffset]::Now.ToUnixTimeSeconds()
  $elapsed = $nowUnix - [int]$state.last_run_unix
  if ($elapsed -lt $RateLimitSeconds) {
    $wait = $RateLimitSeconds - $elapsed
    Tg $channel $target ("STATUS rate-limited; try again in {0}s" -f $wait)
    exit 0
  }
  $state.last_run_unix = $nowUnix
  Save-Json $statePath $state

  $t0 = (Get-Date).ToString('s')
  Tg $channel $target "STATUS start; time=$t0"

  Push-Location $repo
  try {
    $gwPort = 18789

    # gateway
    $gw = $null
    try {
      $gwRaw = (clawdbot gateway status --json | Out-String)
      if ($gwRaw) { $gw = $gwRaw | ConvertFrom-Json }
    } catch {}

    $gwPid = $null
    $gwOk = $false
    try {
      $gwOk = [bool]($gw.rpc.ok)
      if ($gw.port.listeners -and $gw.port.listeners.Count -gt 0) { $gwPid = $gw.port.listeners[0].pid }
    } catch {}

    # health (clowbot)
    $health = $null
    try {
      $hraw = (curl.exe --max-time 2 -sS http://localhost:8000/health)
      if ($hraw) { $health = $hraw | ConvertFrom-Json }
    } catch {}

    # last artifacts (smoke/e2e)
    $smokePath = Join-Path $artDir 'smoke_last.json'
    $e2ePath = Join-Path $artDir 'e2e_last.json'
    $smoke = Read-JsonOrNull $smokePath
    $e2e = Read-JsonOrNull $e2ePath
    $smokeTime = File-TimeOrNull $smokePath
    $e2eTime = File-TimeOrNull $e2ePath

    $t1 = (Get-Date).ToString('s')

    $depsPg = $null; $depsR = $null; $depsQ = $null; $depsM = $null
    try { $depsPg = $health.deps.postgres } catch {}
    try { $depsR = $health.deps.redis } catch {}
    try { $depsQ = $health.deps.qdrant } catch {}
    try { $depsM = $health.deps.minio } catch {}

    $healthOk = $null
    try { $healthOk = [bool]$health.ok } catch {}

    # gw_diag: task last run/result + audit ok + lock files + rpc error short
    $taskLastRun = $null
    $taskLastResult = $null
    try {
      $info = Get-ScheduledTaskInfo -TaskName 'Clawdbot Gateway' -ErrorAction Stop
      $taskLastRun = $info.LastRunTime.ToString('s')
      $taskLastResult = [string]$info.LastTaskResult
    } catch {
      # fallback: leave nulls
    }

    $auditOk = $null
    try { $auditOk = [bool]$gw.service.configAudit.ok } catch {}

    $lockRoots = @(
      (Join-Path $env:LOCALAPPDATA 'Temp\\clawdbot'),
      (Join-Path $env:TEMP 'clawdbot'),
      (Join-Path $env:USERPROFILE '.clawdbot')
    )
    $lockFiles = @()
    foreach ($r in $lockRoots) {
      try {
        if (Test-Path -LiteralPath $r) {
          $lockFiles += Get-ChildItem -LiteralPath $r -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'gateway*.lock' -or $_.Name -like 'gateway*.pid' }
        }
      } catch {}
    }
    $lockLines = @()
    foreach ($f in ($lockFiles | Sort-Object LastWriteTime -Descending | Select-Object -First 5)) {
      $lockLines += (SafePath $f.FullName)
    }

    $rpcErrShort = $null
    try {
      if (-not $gwOk) {
        $e = [string]$gw.rpc.error
        if ($e) {
          $e = ($e -replace "\s+", ' ').Trim()
          if ($e.Length -gt 120) { $e = $e.Substring(0,120) }
          $rpcErrShort = $e
        }
      }
    } catch {}

    if ($gwOk -and $health -and $healthOk -eq $true) {
      $msg = @(
        'STATUS OK',
        ("time: {0}" -f $t1),
        ("gw: ok={0} pid={1} port={2}" -f $gwOk, $gwPid, $gwPort),
        ("api: health_ok={0}" -f $healthOk),
        ("deps: pg={0} r={1} q={2} m={3}" -f $depsPg, $depsR, $depsQ, $depsM),
        ("last_smoke: {0}" -f (Summarize-Last $smoke $smokeTime)),
        ("last_e2e:   {0}" -f (Summarize-Last $e2e $e2eTime)),
        ("gw_diag: task_last_run={0} task_last_result={1} audit_ok={2}" -f $taskLastRun,$taskLastResult,$auditOk)
      )

      if ($lockLines.Count -gt 0) {
        $msg += 'lock_files:'
        $msg += $lockLines
      }
      if ($rpcErrShort) {
        $msg += ("rpc_error_short={0}" -f $rpcErrShort)
      }

      Tg $channel $target ($msg -join "`n")
      exit 0
    }

    # FAIL: include gw_diag + lock files + rpc_error_short (mobile-first)
    $reason = 'unknown'
    if (-not $gwOk) { $reason = 'gw_not_ready' }
    elseif (-not $health) { $reason = 'health_unreachable' }
    elseif ($healthOk -ne $true) { $reason = 'health_not_ok' }

    $ts = (Get-Date).ToString('yyyyMMdd-HHmmss')
    $fail = Join-Path $artDir ("status_fail_$ts.log")

    try {
      $details = @(
        ("time={0}" -f $t1),
        ("reason={0}" -f $reason),
        ("gw_ok={0} gw_pid={1} gw_port={2}" -f $gwOk, $gwPid, $gwPort),
        ("rpc_error_short={0}" -f $rpcErrShort),
        ("health_ok={0}" -f $healthOk),
        ("deps_pg={0} deps_r={1} deps_q={2} deps_m={3}" -f $depsPg, $depsR, $depsQ, $depsM),
        ("task_last_run={0} task_last_result={1} audit_ok={2}" -f $taskLastRun,$taskLastResult,$auditOk),
        'lock_files:',
        ($lockLines -join "`n"),
        ("smoke_last: {0}" -f (Summarize-Last $smoke $smokeTime)),
        ("e2e_last:   {0}" -f (Summarize-Last $e2e $e2eTime))
      ) -join "`n"
      $details | Set-Content -LiteralPath $fail -Encoding UTF8
    } catch {}

    $msg = @(
      'STATUS FAIL',
      ("time: {0}" -f $t1),
      ("reason: {0}" -f $reason),
      ("gw: ok={0} pid={1} port={2}" -f $gwOk, $gwPid, $gwPort),
      ("api: health_ok={0}" -f $healthOk),
      ("deps: pg={0} r={1} q={2} m={3}" -f $depsPg, $depsR, $depsQ, $depsM),
      ("gw_diag: task_last_run={0} task_last_result={1} audit_ok={2}" -f $taskLastRun,$taskLastResult,$auditOk),
      ("fail_log: {0}" -f (SafePath $fail))
    )
    if ($lockLines.Count -gt 0) {
      $msg += 'lock_files:'
      $msg += $lockLines
    }
    if ($rpcErrShort) {
      $msg += ("rpc_error_short={0}" -f $rpcErrShort)
    }

    Tg $channel $target ($msg -join "`n")
    exit 1
  } finally {
    Pop-Location -ErrorAction SilentlyContinue
  }
} catch {
  $ts = (Get-Date).ToString('yyyyMMdd-HHmmss')
  $fail = Join-Path $artDir ("status_fail_$ts.log")
  try {
    ("STATUS exception: " + $_.Exception.Message + "`n") | Set-Content -LiteralPath $fail -Encoding UTF8
  } catch {}
  $t1 = (Get-Date).ToString('s')
  try {
    Tg $channel $target ("STATUS FAIL: exception fail_log={0}" -f (SafePath $fail))
  } catch {}
  exit 1
} finally {
  Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
}
