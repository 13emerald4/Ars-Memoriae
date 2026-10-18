# Ars Memoriae

> *"I cannot teach anybody anything. I can only make them think."* — Socrates  
> *"Entities should not be multiplied beyond necessity."* — William of Ockham

**Ars Memoriae** is an active-recall and knowledge mastery workbench. It rejects the illusions of passive flashcards, the bloat of containerized infrastructure, and the paralysis of infinite review debt.

Everything runs 100% locally. Zero cloud subscriptions, zero telemetry, zero Docker overhead.

---

## The First Principles

### I. Why Type Instead of Flip?
*Can one truly know a concept if one only recognizes it when revealed?*  
Traditional flashcards rely on passive recognition: flip the card, read the answer, and convince yourself that you "knew it." Ars Memoriae requires active retrieval: you type your answer. A local open-weights model (Qwen 2.5 Coder via Ollama) evaluates your semantic understanding against the rubric, accompanied by an instantaneous token-level n-gram overlap heuristic. You accept or override; the system calibrates to your personal judgment over time.

### II. Why a Priority Queue Instead of a Due-Date List?
*Why should missing three days of study punish you with an insurmountable wall of 800 cards?*  
Standard spaced repetition treats cards like calendar appointments, turning life interruptions into demoralizing debt. Ars Memoriae replaces due-date lists with a bounded daily time budget. An FSRS-driven priority queue ranks cards by memory decay and urgency, interleaves concepts with reading extracts, and smooths backlogs so you never face review paralysis.

### III. Why Code in the Review Loop?
*Can software construction be mastered purely through abstract definitions?*  
Syntax, invariants, and algorithms cannot be learned in a vacuum. Ars Memoriae features an interactive, dual-pane Code Lab with live isolated execution (Python & TypeScript), automated unit test harnesses, resizable IDE panels, and a Socratic guide that offers diagnostic clues without spoiling the solution.

### IV. Occam's Architecture: Radical Simplicity
*Why require Docker, external databases, cloud services, and build chains for personal learning?*  
Ars Memoriae is deliberately lean:
- **Single embedded SQLite file** (`backend/dev.db`) — zero database administration.
- **Precompiled production frontend** — no Node.js required to run.
- **Local Ollama daemon** — zero API fees, complete privacy.
- **1-Click native launchers** — start with a single double-click.

---

## Quickstart (Under 3 Minutes)

### Prerequisites
1. **Python 3.11+** installed ([python.org](https://www.python.org/downloads/))  
   *(On Windows: Check **"Add python.exe to PATH"**).*
2. **Ollama** installed ([ollama.com](https://ollama.com)) for local AI grading and Socratic tutoring.

### 1-Click Launch
- **Windows**: Double-click `start.bat` (or `start_windows.bat`).
- **macOS / Linux**: Run `./start.sh` (or `./start_mac.sh`).

On first launch, the script:
1. Prepares the local Python virtual environment.
2. Initializes your private SQLite database with automated schema migrations.
3. Automatically inspects your CPU/GPU hardware and pulls the recommended model (`1.5b`, `3b`, or `7b`).
4. Launches your default web browser to **`http://localhost:8000`**.

> **Sharing with Friends?** See the step-by-step **[FRIENDS_SETUP.md](FRIENDS_SETUP.md)**.

---

## Core Capabilities

| Capability | How It Works | First Principle |
|---|---|---|
| **Active Typing & Local LLM Rubric** | You type your answer; a local Ollama model grades accuracy and explains missed nuances. | Prevents the illusion of competence. |
| **Token-by-Token Similarity Heuristic** | Jaccard + character-trigram similarity cross-checks semantic AI evaluations against verbatim recall. | Redundant verification eliminates false positives. |
| **FSRS Priority Queue** | Free Spaced Repetition Scheduling (FSRS 6.x) with daily time budgets, interval fuzzing, and backlog smoothing. | Bounded daily effort over crushing backlogs. |
| **Adjustable Review Workbench** | Resizable splitters between problem, solution, tests, and console; side-by-side tiled comparisons; 3-column LeetCode dock; column swapping. | Adapt the environment to the complexity of the problem. |
| **Isolated Code Execution Sandbox** | Subprocess runner executing code against custom and starter test cases with timeout guards. | Truth is verified by execution. |
| **Hierarchical Knowledge Tree** | Organize courses, chapters, and topics into navigable branches with drag-and-drop ordering and visual rollup bars. | Knowledge is a tree, not an unstructured pile of leaves. |
| **Incremental Reading** | Ingest articles or documentation, split passages into extracts, and generate targeted cards directly from context. | Learning begins with comprehension of source material. |
| **Interference Detection** | Identifies confusable sister cards before they cause cognitive interference and separates them in review sessions. | Disambiguate similar concepts early. |
| **Feature Requests & Feedback** | Built-in submission panel in Settings with 1-click GitHub Issue creation, markdown formatting, and local history. | Continuous iterative refinement. |

---

## Local Development & Customization

```bash
# Backend (FastAPI + SQLite / Alembic)
cd backend
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"      # macOS/Linux: .venv/bin/pip install -e ".[dev]"
.venv/Scripts/alembic upgrade head
.venv/Scripts/uvicorn app.main:app --reload --port 8000

# Frontend (React 18 + Vite + Tailwind + Monaco Editor)
cd frontend
npm install
npm run dev
```

### Running Test Suites
```bash
cd backend
.venv/Scripts/pytest -q                   # Comprehensive unit and integration test suite

cd frontend
npm run build                             # TypeScript verification and asset bundling
```

---

## Philosophy & Data Sovereignty

- **Your data belongs to you**: All decks, notes, reviews, and logs live in `backend/dev.db`. Backup is as simple as copying that single file.
- **Export anytime**: Complete full-fidelity JSON and CSV review logs via `GET /api/export` and `GET /api/export/review-logs.csv`.
- **Zero lock-in**: Clean, well-documented schemas with full Alembic migration history.

```
"Truth is confirmed by inspection and delay; falsehood by haste and uncertainty." — Tacitus
```
