# Ars Memoriae — Friend Quickstart Guide

Welcome to **Ars Memoriae**! This guide will get you up and running on your own computer in under 3 minutes.

> **Zero Cloud Fees & 100% Private**: Ars Memoriae runs entirely on your machine. Your flashcards, coding progress, and study data are stored locally in an encrypted SQLite database on your own computer.

---

## 1. Prerequisites

- **Python 3.11 or higher** (Required)
  - Download from: [https://www.python.org/downloads/](https://www.python.org/downloads/)
  - **CRITICAL ON WINDOWS**: Check the box **"Add python.exe to PATH"** at the bottom of the installer window!
- **Ollama** (Recommended)
  - Download from: [https://ollama.com](https://ollama.com) for private, offline AI answer grading and Socratic tutoring.
- *(Optional)* **Node.js**: Only needed if you plan to write and run TypeScript or JavaScript exercises in the Code Lab (Python code works out of the box with zero setup).

*(You do **NOT** need Docker or PostgreSQL! Everything runs locally with an embedded SQLite database and precompiled frontend.)*

---

## 2. Download the App

Choose whichever method you prefer:

### Option A: Download the ZIP (Simplest)
1. On GitHub (`https://github.com/13emerald4/Ars-Memoriae`), click the green **Code** button and select **Download ZIP**.
2. Right-click and extract the `.zip` file anywhere (e.g. your Documents or Desktop).

### Option B: Clone via Git (Recommended for Automatic Updates)
Open Terminal or PowerShell and run:
```bash
git clone https://github.com/13emerald4/Ars-Memoriae.git
cd Ars-Memoriae
```

---

## 3. Launching (1-Click)

### Windows
Double-click **`start_windows.bat`** in the `Ars-Memoriae` folder.

### macOS / Linux
Open your Terminal, navigate to the folder, and run:
```bash
chmod +x start_mac.sh
./start_mac.sh
```

**What happens next?**
- On first launch, the script automatically installs dependencies and sets up your local database (~1 minute).
- Your default web browser will automatically open to:
  **`http://localhost:8000`**
- To stop Ars Memoriae, simply close the launcher window or press `Ctrl + C`.

---

## 4. Automatic Hardware Inspection & AI Sizing

Ars Memoriae automatically inspects your computer's hardware specs (RAM, GPU, VRAM) on first download and selects the best model size:
- **1.5B (~986 MB)**: Recommended for laptops with 8 GB RAM or modest CPUs.
- **3B (~1.9 GB)**: The sweet spot for gaming laptops (6-8 GB VRAM), Apple Silicon (8 GB), or 16 GB+ PCs.
- **7B (~4.7 GB)**: For desktop GPUs with 12 GB+ VRAM or Apple Silicon with 16 GB+ unified memory.

### Setup Steps:
1. Download and install [Ollama](https://ollama.com).
2. Start Ars Memoriae using `start.bat` (Windows) or `./start.sh` (macOS/Linux).
   - The launcher will automatically inspect your specs, recommend the ideal size, and pull it for you!
   - You can also inspect your specs manually at any time by running:
     ```bash
     python scripts/detect_hardware.py
     ```
3. In Ars Memoriae, open **Settings** to view your **Hardware Profile** and switch models with 1 click.

---

## 5. Updates & Data Backups

- **Interactive Update Prompts**: If you cloned via Git, double-clicking `start_windows.bat` or running `./start_mac.sh` checks for new updates on startup. If an update has been pushed, it shows the recent changes and prompts you (`[Y/n]`) before updating.
- **Your Data is 100% Safe**: Updating code **never** deletes your study cards, intervals, or coding progress.
- **Backing Up Your Progress**: Your study data lives in a single file at `backend/dev.db`. To back up your progress, simply copy `backend/dev.db` to a safe location (e.g. Google Drive, OneDrive, or a USB drive).

---

## 6. Troubleshooting & FAQ

#### Q: The window says `'python' is not recognized as an internal or external command`.
**Fix**: Python is installed, but was not added to your system PATH. Re-run the Python installer, select **Modify**, and make sure **"Add Python to environment variables"** is checked. Then restart the launcher.

#### Q: How do I change the port if port 8000 is already in use?
**Fix**: Edit `start_windows.bat` or `start_mac.sh` and change `--port 8000` to `--port 8080` (or any available port).

#### Q: Where are my cards and progress stored?
**Fix**: Inside `backend/dev.db`. It's a lightweight SQLite database file stored on your own disk.
