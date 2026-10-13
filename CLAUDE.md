# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A spaced-repetition web app combining FSRS scheduling with LLM-graded typed answers and incremental reading. Users type their answers rather than self-grading; a small local LLM (Qwen 2.5 Coder via Ollama) grades it with reasoning shown. A priority queue (not a due-date list) ranks reviews, new cards, and reading extracts to fill a daily time budget.

**Stack:** FastAPI backend with SQLAlchemy/AsyncPG (Postgres) or SQLite, React+TypeScript frontend with Vite, Docker Compose for deployment.

## Development Commands

### Backend (Python 3.11+)

```bash
cd backend
python -m venv .venv && .venv/bin/pip install -e ".[dev]"  # Windows: .venv\Scripts\pip
.venv/bin/alembic upgrade head                              # Run migrations
.venv/bin/uvicorn app.main:app --reload --port 8000        # Dev server

# Testing
.venv/bin/pytest -q                   # Run all 420+ tests
.venv/bin/pytest tests/test_grading.py  # Single test file
.venv/bin/pytest -k test_name         # Run specific test by name

# Linting
.venv/bin/ruff check .
.venv/bin/ruff format .
```

Backend defaults to SQLite in development; Postgres is optional unless testing migrations.

### Frontend (Node.js)

```bash
cd frontend
npm install
npm run dev         # Dev server (port 5173)
npm run build       # TypeScript check + Vite build
npm run typecheck   # Type-check only (no build)
```

### Docker Compose

```bash
# First time: generate secrets
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(48))"
# Add it to .env along with POSTGRES_PASSWORD

docker compose up --build
```

Migrations run automatically on backend startup.

### Migrations

```bash
cd backend
.venv/bin/alembic revision -m "description"  # Create new migration
.venv/bin/alembic upgrade head               # Apply migrations
.venv/bin/alembic downgrade -1               # Rollback one migration
```

Migrations use type-compatible aliases (JSONType, StringArray, TS) that map to native Postgres types (`JSONB`, `TEXT[]`, `TIMESTAMPTZ`) or JSON/DateTime on SQLite.

## Architecture

### Core Concept: The Registry Pattern

Three extension points ("seams") are resolved through `app/services/registry.py` rather than direct calls:

- **`renderer`**: How note types render to card front/back (basic, cloze, image occlusion)
- **`grading_profile_selector`**: Which rubric to use (short_answer, conceptual, math_code)
- **`queue_composer`**: How the review queue is assembled and ranked

First-party implementations register themselves in `app/services/rendering.py` and `app/services/queue_service.py`. Plugins can override any seam by registering with `default=True`.

### Request Flow

1. **Auth**: JWT tokens (14-day expiry), validated via `app/routers/deps.py:current_user()`
2. **Routing**: `app/main.py` includes routers from `app/routers/` (auth, decks, queue, review, sources, imports, etc.)
3. **Services**: Business logic in `app/services/` (fsrs_service, grading_service, queue_service, ir_service)
4. **Models**: SQLAlchemy ORM in `app/models/`, 1:1 with database schema
5. **Schemas**: Pydantic request/response contracts in `app/schemas/`

### Database Schema Evolution

The schema has evolved through 20 migrations:

- **0001_initial.py**: Core tables (users, decks, note_types, notes, cards, sources, extracts, reviews)
- **0002_sister_pairs.py**: Sister-card interference tracking
- **0003_queue_indexes.py**: Covering indexes for queue performance (112ms target)
- **0004–0009**: Knowledge tree, card references, reading sources, lessons, mastery gating, study sessions
- **0010–0019**: Velocity, reflection, analytics, memory-champion fields, code practice, weakness memory, lexicon, module visibility, deck documentation
- **0020**: `users.timezone` (study-day boundary) and an index on `review_logs.reviewed_at`

When writing migrations, use the frozen type aliases at the top of each migration file (JSONType, StringArray, TS) to ensure Postgres/SQLite compatibility.

### Key Services

**`app/services/fsrs_service.py`**
Wraps `py-fsrs` 6.x. Cards carry Difficulty/Stability/Retrievability. Intervals are fuzzed (±5%), backlogs are smoothed over `spread_days`, and `new` state is app-level (FSRS only has `Learning`/`Review`/`Relearning`).

**`app/services/grading_service.py`**
Calls the local Ollama daemon (`OLLAMA_BASE_URL`, default model `qwen2.5-coder:7b`); no API key. Requests JSON output and parses it tolerantly. Implements:
- Rubric profiles (short_answer, conceptual, math_code)
- Escalation to `ESCALATION_GRADING_MODEL` (low confidence, repeated overrides, math/code cards); no-op when it equals the grading model
- Heuristic cross-check (keyword overlap vs. LLM grade)
- Calibration bias from user overrides
- Answer caching keyed on `(card_id, answer_hash)`

**`app/services/queue_service.py`**
Composes the priority queue:
1. Load bounded candidate pool (500–5,000 cards, not entire collection)
2. Compute overdue boost from FSRS retrievability (not raw days)
3. Rank by priority + boost
4. Fill time budget by stream weights (due/new/extracts)
5. Interleave results

**Performance note:** Never load the entire collection to return one card. Always use bounded queries and covering indexes (migration 0003).

### Frontend Structure

**`frontend/src/api/client.ts`**
Typed API client with auth headers. All endpoints go through this.

**`frontend/src/pages/`**
Top-level routes (Review, Read, Decks, Stats, Settings, Tree, Login). The Review page handles both card reviews and reading extracts by switching on the `kind` field from `/api/queue/next`.

**`frontend/src/components/Occlusion.tsx`**
Image occlusion editor (drag masks) and masked card renderer (all regions stay masked, tested one is highlighted).

### Plugins (§12)

Plugins are **trusted local code** that run with the backend's full privileges (database, filesystem, secrets). They are NOT sandboxed. Only enable via `PLUGIN_DIR` on instances you solely operate.

A plugin is a `.py` file exporting `setup(api)`:

```python
def my_strategy(note_type_profile, template_kind):
    # Your logic here
    return "conceptual"

def setup(api):
    api["register"]("grading_profile_selector", "my_plugin", my_strategy, default=True)
```

Loaded plugins report at `GET /api/plugins` (including failures with tracebacks). See `backend/plugins.example/` for a working example.

### Security Properties (Tested)

- **SSRF containment**: User-submitted URLs (`POST /api/sources`) are validated per redirect hop. Private IPs (169.254.x.x, 127.x.x.x, RFC1918) are blocked unless `URL_FETCH_ALLOW_PRIVATE=1`.
- **Tenant isolation**: Object-scoped routes check ownership before access (parametrized tests across 14 endpoints).
- **Secrets**: Passwords are scrypt-hashed. Code-practice workers run with a scrubbed environment so user code can't read `SECRET_KEY` or `DATABASE_URL`.
- **Uploads**: Server-generated random filenames, content-type allowlist, 20 MB cap.

**Known limitation:** Media URLs (`/media/<user-id>/<random>.png`) are capability URLs served without auth. ~96 bits of entropy makes them unguessable but not access-controlled.

## Testing Philosophy

Coverage spans the entire review cycle, FSRS fuzzing/backlog smoothing, grading rubrics/escalation/caching/fallback, queue composition, JSON import, interference detection, image occlusion, plugin loading, security properties (SSRF, cross-tenant access), and bounded-work guarantees.

**When adding features:**
- Add tests for the happy path, edge cases, and failure modes
- Security-sensitive features (auth, uploads, external fetches) need explicit tests
- Queue/database features should assert bounded work (no O(n) on collection size)

## Common Pitfalls

1. **Don't load the entire collection to return one card.** Use bounded candidate pools and covering indexes.
2. **py-fsrs sleeps 1ms per Card construction** if you don't pass `card_id`. Always pass one (even a constant) to avoid accidental delays.
3. **Postgres vs SQLite types:** Use the aliases (JSONType, StringArray, TS) in migrations, not raw JSONB/ARRAY.
4. **FSRS has no `new` state.** Map it on the way in/out; internally use `Learning`.
5. **Models wrap JSON in prose or code fences.** Always parse LLM output with the tolerant `parse_json`, never `json.loads` directly.
6. **Don't mutate the grading model instance.** Pass the escalated model per call, not by reassigning `self.model`.
7. **"Today" is the user's study day**, not a UTC date: their time zone (`users.timezone`), rolling over at 04:00. Use `app/core/timeutil.py` (`day_start`, `day_key`) for daily caps and day buckets.

## Environment Variables

Key settings (see `.env.example` for full list):

- **`SECRET_KEY`**: JWT signing (generate with `secrets.token_urlsafe(48)`). Unset → generated on first start into `.secret_key` (`SECRET_KEY_FILE`)
- **`OLLAMA_BASE_URL`**: Where the Ollama daemon listens (default `http://localhost:11434`)
- **`OLLAMA_NUM_CTX`**: Context window sent with every request (default 8192). Ollama drops the *start* of longer prompts — the instructions — so don't shrink it below the longest prompt
- **`DATABASE_URL`**: Postgres or SQLite (`sqlite+aiosqlite:///./db.sqlite3` for dev)
- **`ALLOW_REGISTRATION`**: 0 (default) = only the first account can sign up; 1 = open sign-up
- **`PLUGIN_DIR`**: Path to plugin directory (empty = disabled, the safe default)
- **`ENABLE_BACKGROUND_JOBS`**: Set to 0 to disable nightly FSRS refit and cache eviction
- **`URL_FETCH_ENABLED`**: Set to 0 to disable server-side URL fetching entirely

## API Documentation

Interactive docs: <http://localhost:8000/docs> (OpenAPI/Swagger UI)

Key endpoints:
- `POST /api/auth/register`, `POST /api/auth/login`
- `GET /api/queue/next` → `{kind: "card" | "extract", ...}`
- `POST /api/review/submit` → FSRS update + optional LLM grading
- `POST /api/import/json` → bulk note import
- `GET /api/export` → full JSON dump
- `GET /api/plugins` → loaded plugins and failures

## File Locations

- **Models**: `backend/app/models/` (ORM, 1:1 with schema)
- **Services**: `backend/app/services/` (business logic)
- **Routers**: `backend/app/routers/` (FastAPI endpoints)
- **Schemas**: `backend/app/schemas/` (Pydantic request/response)
- **Migrations**: `backend/alembic/versions/`
- **Tests**: `backend/tests/` (pytest, 420+ tests)
- **Frontend pages**: `frontend/src/pages/`
- **Frontend API client**: `frontend/src/api/client.ts`
- **Plugin example**: `backend/plugins.example/`

## Dependency Notes

- **`fsrs[optimizer]`** pulls in torch (~2GB). Off by default; set `INSTALL_FSRS_OPTIMIZER=1` in docker-compose.yml to enable personalized weight refitting. Without it, everything works on FSRS's default weights.
- **FastAPI** idiom uses `x: T = Depends(...)` / `File(...)`, which Ruff B008 flags as mutable defaults. This is ignored in pyproject.toml.
- **Alembic** migrations run automatically on backend startup in Docker; manually via `alembic upgrade head` in local dev.

## Output Style: Spartan

Blunt Spartan mode for ADHD. Answer-first, arrow points, zero warmth or filler. Maximum signal, minimum words.

Terse mode for an ADHD reader who wants signal, not comfort. Every word earns its place or gets cut.

### Rules

- Answer in line one. No preamble, no restating the question.
- **Answer vs deliverable.** An *answer* (explaining, deciding, advising, reporting) says its point and stops, load-bearing lines only. A *deliverable* you were asked to produce (doc, plan, spec, reconstruction, code) runs as long as the work needs; there the length is the substance. Can't tell which? It's an answer. Keep it lean. Reason as long as you need internally; this trims the reply, never the thinking.
- **Deliverable: ship it bare.** Asked to produce an email, message, commit, or snippet? Output only the thing. No lead-in, no "here's", no sign-off around it.
- **Cut elaboration, never a warning.** Trim examples, options, background. Never trim a risk, caveat, or correctness condition. If leaving it out makes the reader act wrong, it stays.
- **Short does not mean fewer points.** If the answer has three load-bearing parts, keep three. Compress each, drop none.
- Blunt and imperative. State it, don't cushion it. No warmth, no hedging, no transitions.
- Mark each point with a `→` as its own paragraph (`**→ Point.** rest`), blank line between each. Not `-` bullets; terminals collapse them.
- **Bold carries the whole answer.** Bold the lead-in and any key term, number, or warning, so reading only the bold gives the full point and every risk. If the bold alone misses it, the bolding is wrong.
- Cut ruthlessly: no padding, no summary, no repetition, no closing restatement. A point can be one line.
- Plain words. Tag an unavoidable term in five words or fewer.
- Flag risk or uncertainty in one blunt line.
- Never narrate what you're about to do. Do it.
