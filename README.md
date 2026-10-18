# Ars Memoriae

**Ars Memoriae** is an active-recall and knowledge mastery workbench designed to eliminate two pervasive flaws in modern learning tools: the illusion of competence fostered by passive flashcards, and the compounding debt of rigid review schedules.

The system adheres to a single design constraint: **radical parsimony**. It runs entirely on your local machine with zero Docker containers, zero external database servers, zero cloud subscriptions, and zero tracking.

---

## First Principles

### I. Why Type Instead of Flip?
*Can a learner claim to know an idea if they only recognize it when shown the answer?*  
Passive flip-cards test recognition, not retrieval. When shown the reverse side of a card, the human mind rationalizes that it knew the answer all along. Ars Memoriae requires you to type your response before the reference is revealed. A local model (Qwen 2.5 Coder via Ollama) evaluates your semantic understanding against an explicit rubric, cross-checked by an instant token-level overlap heuristic. You accept or override; every correction calibrates future scoring.

### II. Why a Priority Queue Instead of a Due-Date List?
*Why should a three-day absence from study transform a learning routine into an insurmountable penalty of hundreds of overdue cards?*  
Calendar-bound review schedules confuse time elapsed with memory decay. When life interrupts study, due-date queues snowball into review debt that induces abandonment. Ars Memoriae replaces due-date lists with a bounded daily time budget. An FSRS-driven queue ranks cards by memory stability and retrieval probability, smooths backlogs over configurable windows, and interleaves conceptual flashcards with incremental reading extracts.

### III. Why Code in the Review Loop?
*Can programming principles be mastered through verbal abstraction alone?*  
Software construction requires syntactic fluency, invariant preservation, and algorithmic reasoning under constraints. Verbal definitions decay without executable feedback. Ars Memoriae embeds an interactive Code Lab directly into spaced repetition: live execution sandboxes (Python & TypeScript), automated unit test runners, dynamic resizable panels, and a Socratic guide that surfaces diagnostic hints without revealing the solution.

### IV. Architecture Without Extraneous Entities
*Why mandate multi-container orchestration and cloud dependencies for personal study?*  
Every layer of unnecessary operational complexity reduces the longevity and reliability of a learning system:
- **Embedded Storage**: A single SQLite file (`backend/dev.db`) contains your entire knowledge base.
- **Precompiled Interface**: The production web interface is served directly from FastAPI; running the application requires no Node.js runtime.
- **Local Intelligence**: AI grading runs through an offline Ollama instance on your machine, eliminating latency, API keys, and recurring costs.
- **Native 1-Click Launchers**: Windows (`start.bat`) and macOS/Linux (`start.sh`) scripts detect hardware, apply migrations, and launch your browser automatically.

---

## Quickstart (Under 3 Minutes)

### Prerequisites
1. **Python 3.11+** ([python.org](https://www.python.org/downloads/))  
   *(Windows: Ensure **"Add python.exe to PATH"** is checked during installation).*
2. **Ollama** ([ollama.com](https://ollama.com)) for local evaluation and Socratic hints.

### 1-Click Launch
- **Windows**: Double-click `start.bat` (or `start_windows.bat`).
- **macOS / Linux**: Run `./start.sh` (or `./start_mac.sh`).

On first launch, the startup script:
1. Configures the isolated Python virtual environment.
2. Applies database migrations to initialize your private SQLite database.
3. Inspects system memory and GPU capacity to pull the optimal model size (`1.5b`, `3b`, or `7b`).
4. Opens your browser to **`http://localhost:8000`**.

> **Sharing with Friends?** See the step-by-step **[FRIENDS_SETUP.md](FRIENDS_SETUP.md)**.

---

## Core Capabilities

| Dimension | Mechanism | Rationale |
|---|---|---|
| **Active Recall Evaluation** | Typed responses evaluated by local LLM against structured rubrics. | Eliminates passive recognition bias. |
| **Verification Heuristic** | Jaccard token overlap + character-trigram matching. | Prevents LLM hallucinations on sparse inputs. |
| **FSRS Priority Scheduling** | Free Spaced Repetition Scheduler (FSRS 6.x) with daily time budgets and backlog smoothing. | Bounds daily workload and eliminates review paralysis. |
| **Adjustable Review Workbench** | Resizable splitters, side-by-side tiled comparisons, LeetCode-style 3-column dock, and column swapping. | Adapts screen real estate to the complexity of the problem. |
| **Sandboxed Code Execution** | Isolated subprocess runner with unit test verification and execution timeout bounds. | Validates implementation against executable truth. |
| **Hierarchical Knowledge Tree** | Branch, topic, and subdeck organization with drag-and-drop sequencing and recursive progress rollup. | Reflects conceptual dependency structures. |
| **Incremental Reading** | Long-form document ingestion with passage extraction and inline flashcard generation. | Derives knowledge directly from primary sources. |
| **Cognitive Interference Guard** | Identifies confusable card pairs and separates them during review sessions. | Prevents associative interference. |
| **In-App Feedback System** | Dedicated Feature Request panel in Settings with 1-click GitHub issue creation and markdown export. | Direct, friction-free feedback loop. |

---

## Local Development

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
.venv/Scripts/pytest -q                   # Backend unit and integration test suite

cd frontend
npm run build                             # TypeScript verification and asset bundling
```

---

## Data Sovereignty

- **Complete Ownership**: All decks, cards, logs, and settings reside in `backend/dev.db`. Moving or backing up your data requires only copying that file.
- **Portability**: Full export to JSON and CSV available at any time via `GET /api/export` and `GET /api/export/review-logs.csv`.
- **Zero Lock-In**: Transparent schemas, standard SQL, and zero proprietary database formats.
