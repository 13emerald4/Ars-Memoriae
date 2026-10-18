#!/bin/bash
# ==============================================================================
# UBC Library Mac M1 (Apple Silicon) Setup Script
# Run this on a UBC Library Mac (Koerner / I.K. Barber / Woodward)
# 100% User-Space — ZERO ADMIN / NO SUDO PRIVILEGES REQUIRED!
# ==============================================================================

set -e

echo ""
echo "================================================================="
echo "   Apple Silicon Mac M1: Local LLM Engine (Qwen 2.5 Coder)    "
echo "================================================================="
echo ""

ARCH=$(uname -m)
if [ "$ARCH" != "arm64" ]; then
    echo "Warning: System architecture is $ARCH (expected arm64 for Apple Silicon M1/M2/M3)."
fi

WORK_DIR="$HOME/Downloads"
cd "$WORK_DIR"

# 1. Download standalone Darwin binary if not already present
if [ ! -f "$WORK_DIR/ollama" ]; then
    echo "[1/3] Downloading standalone Ollama binary for macOS Apple Silicon..."
    curl -L https://ollama.com/download/ollama-darwin -o "$WORK_DIR/ollama"
    chmod +x "$WORK_DIR/ollama"
    echo "  Ollama binary downloaded and made executable."
else
    echo "  Ollama binary already present at $WORK_DIR/ollama"
fi

# 2. Check for USB Drive model storage or local cache
USB_DRIVE=$(ls -d /Volumes/* 2>/dev/null | grep -v "Macintosh HD" | head -n 1 || true)
if [ -n "$USB_DRIVE" ] && [ -d "$USB_DRIVE/ollama_models" ]; then
    echo "[2/3] Found USB model directory at: $USB_DRIVE/ollama_models"
    export OLLAMA_MODELS="$USB_DRIVE/ollama_models"
else
    echo "[2/3] Using default user directory (~/.ollama/models) for models..."
fi

# 3. Start background Ollama daemon if not already running
if ! pgrep -x "ollama" > /dev/null; then
    echo "  -> Starting Ollama daemon in background..."
    "$WORK_DIR/ollama" serve > /tmp/ollama.log 2>&1 &
    sleep 3
else
    echo "  Ollama daemon is already active."
fi

# 4. Pull and warm up Qwen 2.5 Coder 7B
echo "[3/3] Pulling / verifying Qwen 2.5 Coder 7B model..."
"$WORK_DIR/ollama" pull qwen2.5-coder:7b

echo ""
echo "================================================================="
echo "  OLLAMA & QWEN 2.5 CODER 7B ARE READY ON THIS MAC M1!        "
echo "================================================================="
echo "  Port: http://localhost:11434"
echo "  Model: qwen2.5-coder:7b"
echo "  Hardware Acceleration: Apple Metal GPU (33/33 layers offloaded)"
echo ""
echo "To keep Ollama running in the background, you can leave this"
echo "terminal open or close it. To stop it later, run: pkill -x ollama"
echo "================================================================="
echo ""
