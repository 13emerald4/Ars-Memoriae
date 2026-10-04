@echo off
setlocal enabledelayedexpansion

:: Resolve absolute repository root
set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
for %%i in ("%REPO_ROOT%") do set "REPO_ROOT=%%~fi"

echo [1/3] Checking Ollama (:11434)...
netstat -ano | findstr ":11434.*LISTENING" >nul
if errorlevel 1 (
    echo Starting Ollama serve...
    start /min "Ollama Server" ollama serve
) else (
    echo Ollama is already running.
)

echo [2/3] Checking FastAPI Backend (:8000)...
netstat -ano | findstr ":8000.*LISTENING" >nul
if errorlevel 1 (
    echo Starting FastAPI Backend...
    cd /d "%REPO_ROOT%\backend"
    start /min "FastAPI Backend" "%REPO_ROOT%\backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --port 8000
) else (
    echo FastAPI Backend is already running.
)

echo [3/3] Checking Vite Frontend (:5173)...
netstat -ano | findstr ":5173.*LISTENING" >nul
if errorlevel 1 (
    echo Starting Vite Frontend...
    cd /d "%REPO_ROOT%\frontend"
    start /min "Vite Frontend" cmd /c "npm run dev"
) else (
    echo Vite Frontend is already running.
)

:: Brief wait to allow sockets to bind
ping 127.0.0.1 -n 3 >nul
echo All services verified!
