@echo off
chcp 65001 >nul

REM Startup trigger task should NOT stop/start gateway.
REM It only ensures the main supervisor task is running.

set "GW_HOST=127.0.0.1"
set "GW_PORT=18789"
set "CLAW=%USERPROFILE%\AppData\Roaming\npm\clawdbot.cmd"

REM Fast path #1: rpc ok?
if exist "%CLAW%" (
  "%CLAW%" gateway status --json >nul 2>nul
  if %ERRORLEVEL%==0 exit /b 0
)

REM Fast path #2: TCP port listening?
powershell -NoProfile -Command "try { $c = New-Object Net.Sockets.TcpClient('%GW_HOST%', %GW_PORT%); $c.Close(); exit 0 } catch { exit 1 }" >nul 2>nul
if %ERRORLEVEL%==0 exit /b 0

REM Not healthy yet -> ask the main ONLOGON supervisor task to run.
schtasks /Run /TN "Clawdbot Gateway" >nul 2>nul
exit /b 0
