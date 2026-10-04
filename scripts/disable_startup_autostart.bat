@echo off
set "STARTUP_LNK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Memorize_App_AutoStart.lnk"

if exist "%STARTUP_LNK%" (
    del "%STARTUP_LNK%"
    echo Auto-start has been disabled. The app services will no longer launch automatically on Windows login.
) else (
    echo Auto-start is not currently enabled.
)
pause
