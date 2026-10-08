# Ars Memoria

A spaced-repetition web app that takes the scheduling rigor of SuperMemo, the card/deck
ergonomics of Anki, and the review-quality signals of Mnemosyne — with two structural changes:

- **You type your answer.** A small LLM (Gemma/Gemini, on *your* API key) grades it and shows its
  reasoning. You accept or override; the grade you confirm is what FSRS consumes, and every
  override is logged and fed back as a calibration bias.
- **A priority queue, not a due-date list.** Due reviews, new cards, and Incremental Reading
  extracts are ranked by priority and filled into a daily time budget, then interleaved.

Self-hostable via Docker Compose, imports your existing Anki collection, and exports everything
on demand.

---

## Quick start

### 1-Click Native Launcher (Recommended — Zero Docker)

Ars Memoria runs 100% locally with zero cloud dependencies and zero container overhead using an embedded SQLite database and pre-compiled frontend.

- **Windows**: Double-click `start_windows.bat`
- **macOS / Linux**: Run `./start_mac.sh`

The script automatically sets up the local Python virtual environment, applies database migrations, auto-updates from GitHub, and opens your browser at **<http://localhost:8000>**.

> 💡 **Sharing with Friends?** See the step-by-step **[FRIENDS_SETUP.md](FRIENDS_SETUP.md)** guide.

---

### Docker Compose (Optional)

For containerized environments or production deployments:

```bash
cp .env.example .env
# generate real secrets:
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print('API_KEY_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
# paste both into .env, and set POSTGRES_PASSWORD (matching it inside DATABASE_URL)

docker compose up --build
```

- App: <http://localhost:5173>
- API + interactive docs: <http://localhost:8000/docs>

Migrations run automatically on backend start.

### Local development (no Docker)

```bash
# backend — defaults to SQLite, so Postgres is optional for dev
cd backend
python -m venv .venv && .venv/bin/pip install -e ".[dev]"      # Windows: .venv\Scripts\pip
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload --port 8000

# frontend
cd ../frontend
npm install
npm run dev
```

### Enabling the FSRS parameter optimizer

Personalized weight refitting needs `fsrs[optimizer]`, which pulls in torch (~2 GB). It's off by
default so the image stays small. To enable:

```bash
# docker-compose.yml → services.backend.build.args
INSTALL_FSRS_OPTIMIZER: "1"
```

Without it everything works on FSRS's shipped default weights; `/api/optimize` and the nightly job
report clearly that the extra is missing instead of failing silently.

---

## First run

1. Create an account (first registration seeds a Default deck and four note types).
2. **Settings → Google API key.** Paste a key from [aistudio.google.com](https://aistudio.google.com).
   The key is verified on save and the models it can actually reach are listed — click one to use
   it for grading. It's stored encrypted at rest and never leaves in an export.
3. **Settings → LLM grading → consent.** Off by default. Your typed answers and any reading
   passages you run "LLM assist" on are sent to Google under your own key, so this is an explicit
   opt-in. **Leaving it off is a full path, not a degraded one** — you get the same four
   Again/Hard/Good/Easy buttons Anki has.
4. **Decks → Import from Anki** to bring in a `.apkg`, or add notes by hand.
5. **Review.**

---

## How the pieces work

### Scheduling — FSRS

Built on [`py-fsrs`](https://github.com/open-spaced-repetition/py-fsrs) 6.x, the same algorithm
family Anki ships. Each card carries Difficulty, Stability, and Retrievability; the next interval
comes from stability plus your target retention, which is set per user and overridable per deck
(that per-deck override is the "% bias per subject" control).

**Review-load guardrails** are on by default, because a snowballing backlog — not the algorithm —
is what usually drives people to go algorithm-shopping:

| Guardrail | What it does |
|---|---|
| Interval fuzzing | ±5% jitter on review intervals ≥ 2 days, so cards learned together don't clump on one future day. Learning steps stay exact. |
| Backlog smoothing | Miss a week and you get `today + ceil(backlog / spread_days)`, not all 800 at once. |
| Time budget | You set minutes/day; the composer fills that rather than showing an unbounded list. |
| New-card throttle | Standard new-cards/day cap. |

### Grading — BYOK Gemma/Gemini

Flow: card front → you type → latency captured → LLM returns `{grade, confidence, matched_points,
missed_points, reasoning}` → UI shows the reference answer, the suggested grade, and the reasoning
→ you accept or override.

Reliability measures, all of which have tests:

- **Rubric profiles per note type** — short-answer, conceptual (grades content, not prose), and
  math/code (treats the reference as *one* worked solution and checks result + method separately).
- **Escalation** — low confidence, a card you've overridden twice running, or a math/code card
  goes to the larger model.
- **Heuristic cross-check** — a keyword-overlap score runs alongside the LLM; if the model says
  "good" on an answer sharing nothing with the reference (or "again" on a near-verbatim one), the
  grade is flagged for your confirmation instead of auto-accepting.
- **Caching** — keyed on `(card_id, answer_hash)`, so resubmitting the same answer costs nothing.
- **Calibration** — a running average of your overrides nudges future grades. No fine-tuning.
- **Fallback** — no key, no consent, quota exhausted, or a malformed response all return
  `degraded_to_manual: true` with the reference answer, never an error.

### The queue

```
eligible pool → rank by priority + overdue boost → fill the time budget by
stream weights → interleave
```

The overdue boost is derived from FSRS retrievability rather than raw days late, so "overdue" is
measured against what each card's own stability predicted — and a low-priority card can't starve.
`GET /api/queue/next` returns either a card or a reading extract; the UI routes on `kind`.

### Incremental Reading

Paste text or a URL (fetched and stripped server-side). It's chunked on paragraph boundaries into
extracts, with only the first scheduled so a long article trickles in. While reading you can split
a passage into its own extract, make a cloze from a selection, or ask the model to propose cards —
which, like grading, you approve before anything is created. Extracts shed priority as they're
worked and retire when nothing is left.

### Anki import

`.apkg` files in both collection schemas. Note types, decks (including `Parent::Child`), notes,
cards, media, and review history all map across; suspended state and lapse counts survive.

**On FSRS state:** Anki's SM-2 ease/interval don't map onto D/S, so this doesn't try to convert
them. Instead each card's **real review history is replayed through FSRS**, recovering
stability/difficulty from what you actually did. That needs no torch, so it works on the default
image.

Anything that didn't map cleanly comes back as a warnings list shown prominently in the import
panel — flattened HTML, note types with more templates or fields than our model holds, missing
review history. Newer Anki exports using the compressed collection format are rejected with an
actionable message (re-export with "Support older Anki versions").

### Sister-card interference

Cards interfere when they *look* alike but must be answered differently —
"Capital of Australia?" against "Capital of Austria?". Each candidate pair is scored on both
halves independently and classified:

| Front | Back | Verdict |
|---|---|---|
| similar | different | **interference** — the confusable case |
| similar | similar | **duplicate** — consider deleting one |
| different | similar | **convergent** — two prompts, one answer |

Similarity is token Jaccard blended with character-trigram cosine, weighted *adaptively*: on a
one-word card Jaccard is binary and swamps the only signal that separates "hablar" from
"hablarse", so trigrams carry more weight when there are few tokens. Thresholds were calibrated
against known-confusable and known-unrelated pairs — real confusables bottom out near 0.53,
unrelated pairs top out near 0.30, so the 0.52 cutoff sits in a wide gap.

It runs entirely locally: no embeddings, no API calls, no cost. Candidate pairs are blocked
through an inverted index so a large collection doesn't become O(n²).

Flagged pairs are also **kept apart inside a review session** (Mnemosyne's contribution, §2) —
showing two cards you already mix up back to back is how the interference gets reinforced. That's
a reordering, never a drop.

### Image occlusion

Upload a diagram, drag masks over it, and each mask becomes its own independently scheduled card.
Coordinates are stored as fractions of the image, so a mask lands in the same place at any display
size. During review every region stays masked and the tested one is highlighted — the card asks
"what is *this*" rather than leaking the answer through the other labels.

Regions can carry a label. Labelled ones grade like any short-answer card (the LLM sees the label
as the reference answer); unlabelled ones are reveal-only, which the card says explicitly rather
than rendering blank.

### Leeches

A card crossing the lapse threshold is pulled from the queue, not deleted. If you've opted in, the
model gets the card plus your recent failed answers and proposes one of: a **rewrite**, a **split**
into smaller cards, or a note that the card is **ambiguous** and needs your judgement. Accept,
suspend, or keep it as-is from the Stats page. One call per leech, not per review.

### Plugins

The three seams the architecture was built around — note-type rendering, grading-profile
selection, and queue composition — are resolved through a registry rather than called directly.
The grading-profile seam is now genuinely pluggable from outside the codebase.

```bash
# docker-compose.yml → services.backend.volumes
- ./backend/plugins.example:/srv/plugins:ro
# .env
PLUGIN_DIR=/srv/plugins
```

A plugin is a plain `.py` file exporting `setup(api)`:

```python
def choose_profile(note_type_profile, template_kind):
    if template_kind == "cloze" and note_type_profile == "short_answer":
        return "conceptual"          # cloze prose wants partial credit
    return note_type_profile

def setup(api):
    api["register"]("grading_profile_selector", "cloze_as_conceptual",
                    choose_profile, default=True)
```

`default=True` replaces the first-party strategy; without it the plugin is registered but not
selected. Unknown seam names and non-callable implementations are rejected at load, one broken
plugin can't stop the others or the server, and `GET /api/plugins` reports what loaded — including
failures with their tracebacks summarised.

**The security boundary, stated plainly:** plugins are *trusted local code*, not sandboxed
uploads. They run with the backend's full privileges — database, filesystem, stored API keys.
Loading is off unless `PLUGIN_DIR` is set, and it should stay off on any instance you don't
solely operate. §12 leaves the choice open between a Python entry-point system and a webhook
model; this picks Python because self-hosting is the first-class target (§10), where sandboxing
would be theatre — the operator already owns the container. A hosted multi-tenant deployment wants
the webhook model instead, and it can register through these same seams without changing a single
call site. That's what building the seams first bought.

### Your data

`GET /api/export` returns a full-fidelity JSON dump — decks, note types, notes, cards with live
FSRS state, every review log, sources and extracts. `GET /api/export/review-logs.csv` gives the raw
logs for analysis in a notebook. Both work on a hosted instance too. Your API key is deliberately
excluded from both.

**Self-hosting trade-off, stated plainly:** running this yourself adds no new external dependency
(grading is BYOK either way), but nobody else is operating it. Backups of the Postgres volume and
upgrades are your job.

---

## Testing

```bash
cd backend && .venv/bin/pytest -q     # 184 tests
cd frontend && npm run build          # tsc + vite build
```

Coverage spans the FSRS wrapper and fuzzing, backlog smoothing arithmetic, grading (parsing,
rubrics, escalation, heuristic checks, calibration, caching, fallback), the full review cycle,
queue composition and interleaving, IR chunking/splitting/readability, `.apkg` import against
synthetic collections built in the test suite, interference scoring and classification against
labelled confusable/unrelated pairs, session spacing, image-occlusion slot generation, coordinate
clamping and upload hardening, plugin loading including the failure paths, and the security
properties above — SSRF blocking per redirect hop, cross-tenant access attempts, and secret
handling — plus the bounded-work guarantees that keep queue composition flat as a collection
grows.

The full Docker Compose stack has been run end to end against real Postgres — migrations apply,
the spec's native `uuid` / `jsonb` / `text[]` / `timestamptz` / `bytea` column types land as
written, and the review, interference, reading, media-upload, and export flows all work through
the containers.

---

## Performance

`GET /api/queue/next` runs after every review, so its cost is felt on every
card. Benchmarked against an imported-Anki-sized collection (2,000 due + 28,000 new):

| | per `/api/queue/next` |
|---|---|
| Original | 5,664 ms |
| Bounded queries + exact `COUNT`s | 1,446 ms |
| + no per-card sleep (below) | 240 ms |
| + covering indexes (migration 0003) | **112 ms** |

Three things were wrong:

1. **The composer loaded the whole collection** to return one card — every eligible
   row, with note/note-type/deck eagerly loaded, just to sort and take the top few.
   Counts now come from `COUNT(*)`, and rows come from a bounded candidate pool
   ranked in SQL. Work scales with the *session*, not the collection.
2. **py-fsrs sleeps 1 ms per `Card`** when you don't pass a `card_id` — it derives one
   from the clock and then `time.sleep(0.001)` to avoid collisions. Ranking 500
   candidates meant half a second of pure sleeping, and replaying a large import meant
   minutes of it. We key on our own UUIDs and never read that field, so passing a
   constant makes construction 750× faster (1,499 µs → 2 µs).
3. **The hot queries had no covering index.** Migration 0003 adds them.

The candidate pool is capped (500–5,000 cards). Ranking adds an overdue boost that
only Python can compute, so full ordering can't happen in SQL; the pool is sized far
above any session, making the selection exact in practice and approximate only beyond
a ceiling no user reaches. `tests/test_performance.py` pins all of this, including a
timing assertion that catches the sleep coming back.

## Security

What's enforced, and tested:

- **SSRF containment.** `POST /api/sources` lets a user pick a URL the *server* fetches — an SSRF
  primitive. Every hostname is resolved and every resulting address must be publicly routable, so
  cloud metadata (`169.254.169.254`), loopback, and RFC1918 ranges are refused. Redirects are
  followed by hand and **re-validated per hop**, because a public page that 302s to the metadata
  endpoint would otherwise walk straight past a check on the submitted URL. Bodies stream with a
  5 MB cap. Set `URL_FETCH_ALLOW_PRIVATE=1` to fetch from your own intranet, or
  `URL_FETCH_ENABLED=0` to turn the feature off.
- **Tenant isolation.** Every object-scoped route resolves ownership before acting. A parametrised
  test drives one account's token against another's decks, notes, cards, sources and extracts
  across 14 endpoints and asserts 404 on each, plus the listing and export endpoints, planting a
  note in someone else's deck, and borrowing their note type.
- **Secrets.** Passwords are salted scrypt (stdlib, no bcrypt build step). The BYOK Google key is
  Fernet-encrypted under a key separate from the session-signing secret, is never returned by any
  endpoint, and is excluded from the export. Startup logs a warning if either secret is still a
  dev default.
- **Uploads.** Server-generated random filenames (an uploaded `../../../etc/passwd.png` cannot
  escape the media directory), a content-type allowlist, and a 20 MB cap.

Known limitations, stated rather than hidden:

- **Media URLs are capability URLs.** `/media/<user-id>/<random>.png` is served without auth —
  anyone with the link can fetch it. Names carry ~96 bits of entropy so they're unguessable, but
  this is not access control. Fine for a personal instance; if you host for others and that
  matters, put the media mount behind your reverse proxy's auth.
- **DNS rebinding is only narrowed, not closed.** The guard resolves the hostname and the HTTP
  client resolves it again when connecting, leaving a small TOCTOU window. Closing it fully means
  pinning the connection to the validated IP, which conflicts with TLS SNI/cert validation.
- **Tokens can't be revoked.** JWTs are valid for 14 days; signing out clears the client's copy.
  Rotating `SECRET_KEY` invalidates every session at once (and leaves stored API keys intact,
  which is why they use a separate key).
- **Plugins are trusted code**, not sandboxed — see above.

## Notable deviations from the spec

Everything here was driven by how a library or API actually behaves, not preference.

1. **`FSRS` → `Scheduler`.** py-fsrs 6.x renamed the entry point, moved `Optimizer` behind an
   extra, and has no `new` state — a fresh `Card` starts in `Learning`. `new` is kept as an
   app-level "never reviewed" state and mapped on the way in.
2. **`optimizer_available()` probes for torch.** `from fsrs import Optimizer` *always* succeeds:
   without the extra, the library substitutes a stub that raises at construction. Checking the
   import alone would report the optimizer as installed when it isn't.
3. **Structured output is attempted, not assumed.** Gemma models served through the Gemini API
   reject `response_schema`/`response_mime_type`. The service tries the schema path and falls back
   to prompt-instructed JSON with tolerant parsing, so the same code works on Gemma and Gemini.
4. **`grade_with_escalation` doesn't mutate `self.model`.** The spec sketch reassigned it, which
   would leave the instance permanently escalated for every later card. The model is passed per
   call instead.
5. **Import replays history rather than running the optimizer.** The spec called for running the
   optimizer at import time to back-fill D/S/R — but the optimizer fits *parameters*, not per-card
   state. Replaying each card's own history is what actually recovers D/S, and it doesn't require
   the optional extra. The parameter refit still runs afterwards when torch is present.
6. **Model IDs are configurable and verified.** `gemma-4-e4b-it` / `gemma-4-12b-it` are wired as
   the spec'd defaults, but the app lists what your key can actually reach and warns if the
   configured model isn't among them, rather than failing mid-review on an unavailable ID.
7. **`TEXT[]` → JSON on SQLite.** Postgres keeps the spec's native `JSONB`/`TEXT[]`; SQLite (dev
   and tests) gets JSON variants. Tag filtering therefore happens in Python so it behaves
   identically on both.

## Project layout

```
memorization-app/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── alembic/versions/0001_initial.py   # the §5.1 schema
│   └── app/
│       ├── core/          config, auth, at-rest key encryption
│       ├── models/        ORM, 1:1 with the schema
│       ├── schemas/       request/response contracts
│       ├── routers/       auth keys decks queue review sources imports stats
│       │                  export optimize media interference
│       ├── services/      fsrs grading queue ir apkg leech note rendering
│       │                  registry interference plugins
│   └── plugins.example/    a working plugin for the grading-profile seam
│       └── jobs/          nightly FSRS refit, cache eviction, IR release
└── frontend/src/
    ├── api/               typed client
    ├── components/        ui, Occlusion (editor + masked card renderer)
    └── pages/             Review Read Decks Stats Settings
```

Note-type rendering, grading-profile selection, and queue composition are resolved through a small
strategy registry rather than being called directly, so exposing one of them as a real plugin API
later is a registration change rather than a rewrite. Nothing is externally loadable yet — that's
deliberate.

## What's not built

Grading is text-only: an occlusion region is graded on its text label, not on the image itself, and
there's no audio/pronunciation grading. Only one of the three seams (grading-profile selection) is
externally pluggable so far — rendering and queue composition are registered through the same
registry but haven't been exercised by a real plugin, and there's no plugin registry/marketplace,
which §12 puts out of scope until there's something to register against. Occlusion notes imported
from Anki keep their captions but not their masks: Anki stores those in a format we don't parse, so
they render as text-only cards and say so.
