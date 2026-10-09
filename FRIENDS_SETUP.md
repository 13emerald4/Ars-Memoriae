# Ars Memoriae — Friend Quickstart Guide 🏛️

Welcome to **Ars Memoriae**! This guide will get you up and running on your own computer in under 3 minutes.

> **Zero Cloud Fees & 100% Private**: Ars Memoriae runs entirely on your machine. Your flashcards, coding progress, and study data are stored locally in an encrypted SQLite database on your own computer.

---

## 1. Prerequisites

You only need **one** requirement:
- **Python 3.11 or higher**
  - Download from: [https://www.python.org/downloads/](https://www.python.org/downloads/)
  - ⚠️ **CRITICAL ON WINDOWS**: Make sure to check the box: **"Add python.exe to PATH"** at the bottom of the installer window!

*(You do **NOT** need Docker, PostgreSQL, or Node.js!)*

---

## 2. Download the App

Choose whichever method you prefer:

### Option A: Download the ZIP (Simplest)
1. Download **`Ars-Memoriae-Release.zip`** from GitHub.
2. Right-click and extract the `.zip` file anywhere (e.g. your Documents or Desktop).

### Option B: Clone via Git (Recommended for Auto-Updates)
Open Terminal / PowerShell and run:
```bash
git clone https://github.com/13emerald4/Ars-Memoriae.git
cd Ars-Memoriae
```

---

## 3. Launching (1-Click)

### 🪟 Windows
Double-click **`start_windows.bat`** in the `Ars-Memoriae` folder.

### 🍎 macOS / 🐧 Linux
Open your Terminal, navigate to the folder, and run:
```bash
chmod +x start_mac.sh
./start_mac.sh
```

**What happens next?**
- On first launch, the script automatically installs dependencies and sets up your local database (~1 minute).
- Your default web browser will automatically open to:
  👉 **`http://localhost:8000`**
- To stop Ars Memoriae, simply close the launcher window or press `Ctrl + C`.

---

## 4. Setting Up AI (Hints, Grading & Code Tutor)

Ars Memoriae's AI features (grading, hints, code tutor) run on **Ollama**, a free program that runs the model on your own computer. Nothing is sent online, and no API key is needed.

*Best on Apple Silicon (M1/M2/M3) or a PC with a gaming GPU. On a slower laptop it still works, just slowly. Without Ollama, the app still works fully with manual grading.*

1. Download and install [Ollama](https://ollama.com).
2. Open a terminal and run:
   ```bash
   ollama run qwen2.5-coder:7b
   ```
3. Ars Memoriae will automatically detect Ollama running on `http://localhost:11434`.
4. In Ars Memoriae, open **Settings (⚙️)** and turn on **LLM grading**.

---

## 5. Updates & Data Backups

- **Automatic Updates**: If you cloned via Git, double-clicking `start_windows.bat` or running `./start_mac.sh` automatically pulls the latest bug fixes and improvements every time you start the app.
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
