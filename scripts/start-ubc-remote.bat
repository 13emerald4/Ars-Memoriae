@echo off
title UBC Library Remote Access Launcher
pwsh.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-ubc-remote.ps1"
if %ERRORLEVEL% NEQ 0 (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-ubc-remote.ps1"
)
pause
