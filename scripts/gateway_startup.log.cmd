@echo off
chcp 65001 >nul
set LOGDIR=C:\Users\maste\clawd\clowbot\scripts\logs
if not exist "%LOGDIR%" mkdir "%LOGDIR%" >nul 2>nul
call "C:\Users\maste\clawd\clowbot\scripts\gateway_startup.cmd" > "%LOGDIR%\gateway_startup.log" 2>>&1
exit /b %ERRORLEVEL%
