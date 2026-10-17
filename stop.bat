@echo off
setlocal enabledelayedexpansion

title Stop Ars Memoriae

echo Stopping Ars Memoriae services...

:: 1. Stop FastAPI Backend on Port 8000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000.*LISTENING"') do (
    echo Stopping Backend process (PID %%a)...
    taskkill /f /pid %%a >nul 2>&1
)

:: 2. Stop Vite Dev Server on Port 5173 (if running in dev mode)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173.*LISTENING"') do (
    echo Stopping Dev Server process (PID %%a)...
    taskkill /f /pid %%a >nul 2>&1
)

echo.
echo All Ars Memoriae services stopped cleanly.
timeout /t 3 >nul
