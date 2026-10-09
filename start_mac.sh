#!/usr/bin/env bash
set -e

# Resolve repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==================================================================="
echo "   🏛️  Ars Memoriae — Zero-Docker Self-Hosted Launcher"
echo "==================================================================="
echo ""

# 1. Check Python
echo "[1/5] Checking Python installation..."
PYTHON_CMD=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "[ERROR] Python 3.11+ is not found on your system!"
    echo "Please install Python using Homebrew (brew install python) or from https://www.python.org/downloads/"
    exit 1
fi

$PYTHON_CMD -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" || {
    echo "[ERROR] Python 3.11+ is required. Please update your Python installation."
    exit 1
}
echo "  Found Python: $($PYTHON_CMD --version)"

# 2. Check for updates if git repository
echo "[2/5] Checking for updates..."
if [ -d ".git" ] && command -v git >/dev/null 2>&1; then
    echo "  Fetching latest updates from GitHub..."
    git pull --ff-only 2>/dev/null || echo "  Note: Offline or local changes detected. Continuing with current version."
else
    echo "  Running from standalone release package."
fi

# 3. Setup Virtual Environment
echo "[3/5] Checking Python virtual environment..."
if [ ! -f "backend/.venv/bin/python" ]; then
    echo "  Creating local virtual environment in backend/.venv..."
    $PYTHON_CMD -m venv backend/.venv
fi
# Re-runs pip whenever backend/pyproject.toml changed, e.g. after the git pull above.
backend/.venv/bin/python scripts/sync_backend_deps.py

# 4. Database Schema Migrations
echo "[4/5] Checking database schema..."
(cd backend && ./.venv/bin/alembic upgrade head)

# 5. Launch Ars Memoriae & Browser
echo "[5/5] Launching Ars Memoriae..."
echo ""
echo "==================================================================="
echo "  Application running at: http://localhost:8000"
echo "  To stop the server, press Ctrl+C in this terminal."
echo "==================================================================="
echo ""

# Open default browser (macOS 'open' or Linux 'xdg-open')
if command -v open >/dev/null 2>&1; then
    (sleep 1 && open http://localhost:8000) &
elif command -v xdg-open >/dev/null 2>&1; then
    (sleep 1 && xdg-open http://localhost:8000) &
fi

cd backend
exec ./.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
