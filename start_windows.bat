@echo off
setlocal enabledelayedexpansion

title Ars Memoriae - Self-Hosted Launcher

echo ===================================================================
echo    Ars Memoriae - Zero-Docker Self-Hosted Launcher
echo ===================================================================
echo.

:: 1. Verify Python Installation
echo [1/5] Checking Python installation...
set "PYTHON_CMD="
where python >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
) else (
    where py >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_CMD=py -3"
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python 3.11+ is not found on your system!
    echo.
    echo Please download and install Python from:
    echo   https://www.python.org/downloads/
    echo.
    echo CRITICAL: Ensure you check "Add python.exe to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: Verify Python version is 3.11+ (backend/pyproject.toml requires it)
%PYTHON_CMD% -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.11+ is required. Please update your Python installation.
    pause
    exit /b 1
)
echo   Found Python: %PYTHON_CMD%

:: 2. Check for Updates from GitHub
echo [2/5] Checking for updates...
%PYTHON_CMD% scripts\check_update.py
if errorlevel 10 (
    echo.
    echo   [INFO] Reloading launcher with updated files...
    "%~f0" %*
    exit /b
)

:: 3. Setup Virtual Environment
echo [3/5] Checking Python virtual environment...
if not exist "backend\.venv\Scripts\python.exe" (
    echo   Creating local virtual environment in backend\.venv...
    %PYTHON_CMD% -m venv backend\.venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)
:: Re-runs pip whenever backend\pyproject.toml changed, e.g. after the git pull above.
backend\.venv\Scripts\python.exe scripts\sync_backend_deps.py
if errorlevel 1 (
    echo [ERROR] Failed to install backend dependencies.
    pause
    exit /b 1
)

:: 4. Database Schema Migrations
echo [4/5] Checking database schema...
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
cd ..

:: Optional Local AI Engine (Ollama) & Hardware Model Sizing
where ollama >nul 2>&1
if not errorlevel 1 (
    netstat -ano | findstr ":11434.*LISTENING" >nul
    if errorlevel 1 (
        echo   Starting local Ollama daemon...
        start /min "Ollama" ollama serve
        timeout /t 2 /nobreak >nul
    )

    :: If no Qwen 2.5 Coder model is present yet, inspect hardware and pull the recommended size
    ollama list | findstr /i "qwen2.5-coder" >nul 2>&1
    if errorlevel 1 (
        echo.
        echo [Hardware Inspection] Analyzing your system specs for the optimal AI model...
        backend\.venv\Scripts\python.exe scripts\detect_hardware.py
        for /f "tokens=*" %%m in ('backend\.venv\Scripts\python.exe scripts\detect_hardware.py --model-only') do set "REC_MODEL=%%m"
        if not "!REC_MODEL!"=="" (
            echo   Downloading recommended model: !REC_MODEL! ...
            ollama pull !REC_MODEL!
        )
    )
)

:: 5. Launch Ars Memoriae & Browser
echo [5/5] Launching Ars Memoriae...
echo.
echo ===================================================================
echo   Application running at: http://localhost:8000
echo   To stop the server, press Ctrl+C or close this window.
echo ===================================================================
echo.

:: Open browser
start "" http://localhost:8000

:: Start server
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
