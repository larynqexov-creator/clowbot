@echo off
chcp 65001 >nul
REM Delay 60s to let network/docker/etc settle
timeout /t 60 /nobreak >nul
call "C:\Users\maste\.clawdbot\gateway.cmd"
exit /b %ERRORLEVEL%
