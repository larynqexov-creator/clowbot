@echo off
chcp 65001 >nul
REM Delay 180s to let Docker Desktop come up
timeout /t 180 /nobreak >nul
call "C:\Users\maste\clawd\clowbot\scripts\smoke_startup.cmd"
exit /b %ERRORLEVEL%
