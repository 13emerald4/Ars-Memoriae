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

:: Verify Python version is 3.10+
%PYTHON_CMD% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.10+ is required. Please update your Python installation.
    pause
    exit /b 1
)
echo   Found Python: %PYTHON_CMD%

:: 2. Auto-Update from GitHub if running in a Git repository
echo [2/5] Checking for updates...
if exist ".git" (
    where git >nul 2>&1
    if not errorlevel 1 (
        echo   Fetching latest updates from GitHub...
        git pull --ff-only 2>nul
        if errorlevel 1 (
            echo   Note: Continuing with current local version.
        ) else (
            echo   Repository is up to date.
        )
    ) else (
        echo   Git not in PATH. Skipping auto-update.
    )
) else (
    echo   Running from standalone release package.
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
    echo   Installing backend dependencies (this only happens on first run)...
    backend\.venv\Scripts\python.exe -m pip install --upgrade pip >nul 2>&1
    backend\.venv\Scripts\python.exe -m pip install -e backend
    if errorlevel 1 (
        echo [ERROR] Failed to install backend dependencies.
        pause
        exit /b 1
    )
)

:: 4. Database Schema Migrations
echo [4/5] Checking database schema...
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
cd ..

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
