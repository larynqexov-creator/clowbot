@echo off
chcp 65001 >nul
set LOGDIR=C:\Users\maste\clawd\clowbot\scripts\logs
if not exist "%LOGDIR%" mkdir "%LOGDIR%" >nul 2>nul
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "C:\Users\maste\clawd\clowbot\scripts\e2e_always_on.ps1" >> "%LOGDIR%\e2e_always_on.log" 2>>&1
exit /b %ERRORLEVEL%
