@echo off
chcp 65001 >nul
set LOGDIR=C:\Users\maste\clawd\clowbot\scripts\logs
if not exist "%LOGDIR%" mkdir "%LOGDIR%" >nul 2>nul
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "C:\Users\maste\clawd\clowbot\scripts\telegram_router.ps1" >> "%LOGDIR%\telegram_router.log" 2>>&1
exit /b %ERRORLEVEL%
