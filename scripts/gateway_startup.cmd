@echo off
chcp 65001 >nul
setlocal

set "GW_HOST=127.0.0.1"
set "GW_PORT=18789"
set "READY_TIMEOUT_S=30"

REM Make sure the user's npm bin dir is on PATH (where clawdbot.cmd typically lives)
set "NPMBIN=%USERPROFILE%\AppData\Roaming\npm"
set "PATH=%NPMBIN%;%PATH%"

REM Resolve absolute path to clawdbot executable
set "CLAWDBOT="
for /f "usebackq delims=" %%I in (`where clawdbot 2^>nul`) do (
  set "CLAWDBOT=%%I"
  goto :found
)
if exist "%NPMBIN%\clawdbot.cmd" set "CLAWDBOT=%NPMBIN%\clawdbot.cmd"
:found
if not defined CLAWDBOT (
  echo ERROR: clawdbot executable not found via PATH or "%NPMBIN%\clawdbot.cmd".
  exit /b 1
)

REM 1) Fast path: already ready? (rpc ok OR port listening)
call :is_ready
if %ERRORLEVEL%==0 (
  echo Gateway already ready on %GW_HOST%:%GW_PORT%
  exit /b 0
)

REM 2) Start gateway (idempotent)
echo Starting gateway...
call "%CLAWDBOT%" gateway start
if not %ERRORLEVEL%==0 (
  echo ERROR: clawdbot gateway start failed (code %ERRORLEVEL%).
  exit /b %ERRORLEVEL%
)

REM 3) Wait for readiness (poll 1-2s up to 30s)
echo Waiting for gateway readiness (timeout=%READY_TIMEOUT_S%s)...
set /a "elapsed=0"
:wait_loop
call :is_ready
if %ERRORLEVEL%==0 (
  echo Gateway is ready.
  exit /b 0
)
if %elapsed% GEQ %READY_TIMEOUT_S% (
  echo ERROR: gateway not ready after %READY_TIMEOUT_S%s
  exit /b 1
)
timeout /t 2 /nobreak >nul
set /a "elapsed+=2"
goto :wait_loop

:is_ready
REM Check #1: gateway rpc ok (via clawdbot gateway status --json)
call "%CLAWDBOT%" gateway status --json | powershell -NoProfile -Command "$raw=[Console]::In.ReadToEnd(); try { $j=$raw|ConvertFrom-Json } catch { exit 1 }; if ($j -and $j.rpc -and $j.rpc.ok -eq $true) { exit 0 } else { exit 1 }" >nul 2>nul
if %ERRORLEVEL%==0 exit /b 0

REM Check #2: TCP port listening
powershell -NoProfile -Command "try { $c = New-Object Net.Sockets.TcpClient('%GW_HOST%', %GW_PORT%); $c.Close(); exit 0 } catch { exit 1 }" >nul 2>nul
exit /b %ERRORLEVEL%
