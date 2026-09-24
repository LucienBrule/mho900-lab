@echo off
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0taskctl.ps1" %*
exit /b %ERRORLEVEL%
