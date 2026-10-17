#!/usr/bin/env bash
# ==============================================================================
# Stop Ars Memoriae (macOS / Linux)
# ==============================================================================

echo "Stopping Ars Memoriae services..."

# Stop port 8000 (Backend)
if command -v lsof >/dev/null 2>&1; then
    PID_8000=$(lsof -t -i:8000 2>/dev/null || true)
    if [ -n "$PID_8000" ]; then
        echo "Stopping Backend (PID $PID_8000)..."
        kill -9 $PID_8000 2>/dev/null || true
    fi

    PID_5173=$(lsof -t -i:5173 2>/dev/null || true)
    if [ -n "$PID_5173" ]; then
        echo "Stopping Dev Server (PID $PID_5173)..."
        kill -9 $PID_5173 2>/dev/null || true
    fi
else
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
fi

echo "Services stopped cleanly."
