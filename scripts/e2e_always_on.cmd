@echo off
chcp 65001 >nul
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "C:\Users\maste\clawd\clowbot\scripts\e2e_always_on.ps1"
exit /b %ERRORLEVEL%
