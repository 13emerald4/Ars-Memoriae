@echo off
setlocal enabledelayedexpansion

echo Stopping Memorization App services...

:: 1. Stop FastAPI Backend (:8000)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000.*LISTENING"') do (
    echo Stopping Backend PID %%a...
    taskkill /f /pid %%a >nul 2>&1
)

:: 2. Stop Vite Frontend (:5173)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173.*LISTENING"') do (
    echo Stopping Vite Frontend PID %%a...
    taskkill /f /pid %%a >nul 2>&1
)

echo Services stopped cleanly.
pause
