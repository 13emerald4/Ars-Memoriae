"""Create Lab 5 JSON files and import them into Ars Memoriae."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import httpx
from sqlalchemy import select
from app.core.security import create_access_token
from app.db import SessionLocal
from app.models import Card, CardReference, Deck, Import, Note, User
from app.services.note_service import default_note_type, sync_cards

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("import_lab05")

USER_EMAIL = "michael.r.polley@outlook.com"
LABS_DIR = Path(r"C:\Users\micha\OneDrive\Documents\UBC BCS ICS\CPSC 210\06 Flashcards\6 - Labs")

LAB05_CARDS = [
    {
        "card_type": "qa",
        "category": "Architecture",
        "difficulty": "Easy",
        "priority": 90,
        "tags": ["cpsc210", "lab5", "lab", "frontend", "classes", "abstraction"],
        "locator": "Lab05.1 — Lab 5: Watching the Tides — README (intro)",
        "quote": "This is also your first lab written with a class. Everything the page does depends on the same handful of things: its controls, its chart, the function it fetches with, and the day it is showing... Here they become the fields of one Dashboard object, and what the page does becomes its methods.",
        "front": "Lab 5: what are the lab's main goals, and how does the code structure differ from Labs 1–4?",
        "back": "1. **Main goals**: Consume the tide service API in the browser, build pure view functions (Chart.js curve, station options, title, highs/lows), and manage page state and event-driven behaviour inside your first **class** (`Dashboard`).\n2. **Structural difference**: Instead of passing state (controls, chart, fetch function, current day) as parameters through every function, they become **fields of one `Dashboard` object**, and page operations become its **methods**.",
    },
    {
        "card_type": "qa",
        "category": "DOM & Contract",
        "difficulty": "Medium",
        "priority": 90,
        "tags": ["cpsc210", "lab5", "lab", "dom", "contract", "designing-for-failure", "status-codes"],
        "locator": "Lab05.1 — Lab 5: Watching the Tides — README: The Page Contract & Status Codes",
        "quote": "Every Result error, from an unknown station to a service that is down, goes in #message: never a blank page or an unhandled rejection... Every URL in the page and in your code is relative: styles.css, app.js, stations/tofino. Never start one with /.",
        "front": "Lab 5: what is the Page Contract, where must error messages be displayed, and why are all URLs relative?",
        "back": "1. **Page Contract**: Required controls and IDs: `#station` (`<select>`), `#previous-day` & `#next-day` (`<button>` with `aria-label`), `#play` (`<button>` reading \"Play\"/\"Pause\"), `#tides` (`<canvas>`), `#turns` (`<ol aria-label=\"High and low tides\">`), and `#message` (`<p role=\"status\">`).\n2. **Error display**: Every `Result` error goes into `#message.textContent`; on a successful load, `#message` must be cleared.\n3. **Relative URLs**: The page is served behind a path prefix (e.g. `/container/proxy/3000/`); absolute URLs (`/styles.css`, `/stations`) escape the prefix and fail.",
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Lab 5, T1: stationOptions(stations)",
        "category": "View Functions",
        "difficulty": "Easy",
        "priority": 90,
        "tags": ["cpsc210", "lab5", "lab", "code", "view-functions", "immutability", "sorting"],
        "locator": "Lab05.1 — Lab 5: Watching the Tides — TASK T1: The View Functions (stationOptions)",
        "quote": "stationOptions(stations): one { value, label } per station, labelled Title (Region), sorted alphabetically by title. The list it is given is left in its original order.",
        "front": "Lab 5, T1: implement `stationOptions(stations: StationSummary[]): StationOption[]`. Return one `{ value, label }` per station, labelled `\"Title (Region)\"`, sorted alphabetically by title. The input list must NOT be mutated.",
        "starter_code": "type StationSummary = { id: string; title: string; region: string };\ntype StationOption = { value: string; label: string };\n\nfunction stationOptions(stations: StationSummary[]): StationOption[] {\n  // TODO: return options sorted alphabetically by title without mutating stations\n  return [];\n}",
        "back": "type StationSummary = { id: string; title: string; region: string };\ntype StationOption = { value: string; label: string };\n\nfunction stationOptions(stations: StationSummary[]): StationOption[] {\n  return stations\n    .map((s) => ({\n      value: s.id,\n      label: `${s.title} (${s.region})`,\n    }))\n    .sort((a, b) => a.label.localeCompare(b.label));\n}",
        "test_cases": [
            {
                "input": {
                    "stations": [
                        {"id": "tofino", "title": "Tofino", "region": "West Coast"},
                        {"id": "victoria", "title": "Victoria", "region": "South Coast"},
                        {"id": "vancouver", "title": "Vancouver", "region": "South Coast"},
                    ]
                },
                "expected": [
                    {"value": "tofino", "label": "Tofino (West Coast)"},
                    {"value": "vancouver", "label": "Vancouver (South Coast)"},
                    {"value": "victoria", "label": "Victoria (South Coast)"},
                ],
            },
            {
                "input": {
                    "stations": [
                        {"id": "z", "title": "Z", "region": "R"},
                        {"id": "a", "title": "A", "region": "R"},
                    ]
                },
                "expected": [
                    {"value": "a", "label": "A (R)"},
                    {"value": "z", "label": "Z (R)"},
                ],
            },
        ],
        "time_complexity": "O(n log n)",
        "space_complexity": "O(n)",
        "edge_cases": ["Empty stations list", "Already sorted stations", "Reverse sorted stations"],
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Lab 5, T1: stepDay(day, step)",
        "category": "View Functions",
        "difficulty": "Easy",
        "priority": 90,
        "tags": ["cpsc210", "lab5", "lab", "code", "view-functions", "modulo", "boundaries"],
        "locator": "Lab05.1 — Lab 5: Watching the Tides — TASK T1: The View Functions (stepDay)",
        "quote": "stepDay(day, step): the day step days away, wrapping around the month, so the day after 30 is 1 and the day before 1 is 30.",
        "front": "Lab 5, T1: implement `stepDay(day: number, step: number): number`. Move `step` days away, wrapping around the 30-day month (`LAST_DAY = 30`). Day after 30 is 1; day before 1 is 30. Precondition: `day` is 1..30; `step` is an integer.",
        "starter_code": "const LAST_DAY = 30;\n\nfunction stepDay(day: number, step: number): number {\n  // TODO: wrap around [1, LAST_DAY]\n  return day;\n}",
        "back": "const LAST_DAY = 30;\n\nfunction stepDay(day: number, step: number): number {\n  const zeroBased = ((day - 1 + step) % LAST_DAY + LAST_DAY) % LAST_DAY;\n  return zeroBased + 1;\n}",
        "test_cases": [
            {"input": {"day": 5, "step": 1}, "expected": 6},
            {"input": {"day": 5, "step": -1}, "expected": 4},
            {"input": {"day": 30, "step": 1}, "expected": 1},
            {"input": {"day": 1, "step": -1}, "expected": 30},
            {"input": {"day": 1, "step": 30}, "expected": 1},
        ],
        "time_complexity": "O(1)",
        "space_complexity": "O(1)",
        "edge_cases": ["Wrapping forward from 30 to 1", "Wrapping backward from 1 to 30", "Large positive or negative steps"],
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Lab 5, T1: chartTitle(stationTitle, day, readings)",
        "category": "View Functions",
        "difficulty": "Easy",
        "priority": 90,
        "tags": ["cpsc210", "lab5", "lab", "code", "view-functions", "string-formatting"],
        "locator": "Lab05.1 — Lab 5: Watching the Tides — TASK T1: The View Functions (chartTitle)",
        "quote": "chartTitle(stationTitle, day, readings): the chart's title, such as \"Port Alberni, day 17, full moon\"... the data writes the quarter moons as \"first-quarter\" and \"last-quarter\", and the title writes them as words. A day with no readings has no phase to give, so its title is \"Port Alberni, day 17\" .",
        "front": "Lab 5, T1: implement `chartTitle(stationTitle: string, day: number, readings: { phase: string }[]): string`. Return `\"Title, day D, <phase> moon\"` with hyphenated quarter moons converted to words (`\"first quarter\"`, `\"last quarter\"`). If `readings` is empty, return `\"Title, day D\"`.",
        "starter_code": "function chartTitle(stationTitle: string, day: number, readings: { phase: string }[]): string {\n  // TODO: format title with moon phase words or omit if readings empty\n  return \"\";\n}",
        "back": "function chartTitle(stationTitle: string, day: number, readings: { phase: string }[]): string {\n  if (readings.length === 0) {\n    return `${stationTitle}, day ${day}`;\n  }\n  const rawPhase = readings[0].phase;\n  const wordsPhase = rawPhase.replace(\"-\", \" \");\n  return `${stationTitle}, day ${day}, ${wordsPhase} moon`;\n}",
        "test_cases": [
            {
                "input": {
                    "stationTitle": "Port Alberni",
                    "day": 17,
                    "readings": [{"phase": "full"}],
                },
                "expected": "Port Alberni, day 17, full moon",
            },
            {
                "input": {
                    "stationTitle": "Victoria",
                    "day": 8,
                    "readings": [{"phase": "first-quarter"}],
                },
                "expected": "Victoria, day 8, first quarter moon",
            },
            {
                "input": {
                    "stationTitle": "Vancouver",
                    "day": 3,
                    "readings": [],
                },
                "expected": "Vancouver, day 3",
            },
        ],
        "time_complexity": "O(1)",
        "space_complexity": "O(1)",
        "edge_cases": ["Empty readings list", "Quarter moon with hyphen", "Single-word moon phase"],
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Lab 5, T1: turnLabel(turn)",
        "category": "View Functions",
        "difficulty": "Easy",
        "priority": 90,
        "tags": ["cpsc210", "lab5", "lab", "code", "view-functions", "formatting"],
        "locator": "Lab05.1 — Lab 5: Watching the Tides — TASK T1: The View Functions (turnLabel)",
        "quote": "turnLabel(turn): one list item's text: \"High tide at 16:00, 3.47 m\" or \"Low tide at 09:00, 0.62 m\", with a two-digit hour and a height with exactly two decimals.",
        "front": "Lab 5, T1: implement `turnLabel(turn: { kind: \"high\" | \"low\"; hour: number; height: number }): string`. Format as `\"High tide at HH:00, H.HH m\"` or `\"Low tide at HH:00, H.HH m\"`, with two-digit zero-padded hour and height formatted to exactly 2 decimals.",
        "starter_code": "type TideTurn = { kind: \"high\" | \"low\"; hour: number; height: number };\n\nfunction turnLabel(turn: TideTurn): string {\n  // TODO: format \"High tide at HH:00, H.HH m\" or \"Low tide at HH:00, H.HH m\"\n  return \"\";\n}",
        "back": "type TideTurn = { kind: \"high\" | \"low\"; hour: number; height: number };\n\nfunction turnLabel(turn: TideTurn): string {\n  const kindWord = turn.kind === \"high\" ? \"High tide\" : \"Low tide\";\n  const hh = String(turn.hour).padStart(2, \"0\");\n  const hhh = turn.height.toFixed(2);\n  return `${kindWord} at ${hh}:00, ${hhh} m`;\n}",
        "test_cases": [
            {
                "input": {"turn": {"kind": "high", "hour": 16, "height": 3.47}},
                "expected": "High tide at 16:00, 3.47 m",
            },
            {
                "input": {"turn": {"kind": "low", "hour": 9, "height": 0.62}},
                "expected": "Low tide at 09:00, 0.62 m",
            },
            {
                "input": {"turn": {"kind": "high", "hour": 1, "height": 1.6}},
                "expected": "High tide at 01:00, 1.60 m",
            },
        ],
        "time_complexity": "O(1)",
        "space_complexity": "O(1)",
        "edge_cases": ["Single digit hour needs 0-padding (e.g. 09:00)", "Height ending in zero needs 2 decimal places (1.6 -> 1.60)"],
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Lab 5, T1: highsAndLows(readings)",
        "category": "View Functions",
        "difficulty": "Hard",
        "priority": 90,
        "tags": ["cpsc210", "lab5", "lab", "code", "view-functions", "algorithms", "plateau", "extrema"],
        "locator": "Lab05.1 — Lab 5: Watching the Tides — TASK T1: The View Functions (highsAndLows)",
        "quote": "A high is where the water stops rising and starts to fall: a reading higher than the one before it and higher than the next reading of a different height. A low is the same, the other way up... The water often holds at the same height for two hours at the top or bottom. That is still one high or low, reported at the first of those hours. The day's first and last readings are never highs or lows",
        "front": "Lab 5, T1: implement `highsAndLows(readings: { hour: number; height: number }[]): { kind: \"high\" | \"low\"; hour: number; height: number }[]`. Find all tide turns in time order.\nRules:\n1. Only inspect index 1 to len - 2 (hour 0 and last hour are NEVER turns).\n2. For reading at index i, look back to i - 1 and forward to the next reading with a *different* height.\n3. Plateau rule: if water holds the same height for multiple hours, report the turn at the **first** hour only.",
        "starter_code": "type TideTurn = { kind: \"high\" | \"low\"; hour: number; height: number };\n\nfunction highsAndLows(readings: { hour: number; height: number }[]): TideTurn[] {\n  // TODO: find high and low turns in time order, handling held plateaus and excluding hour 0 and last hour\n  return [];\n}",
        "back": "type TideTurn = { kind: \"high\" | \"low\"; hour: number; height: number };\n\nfunction highsAndLows(readings: { hour: number; height: number }[]): TideTurn[] {\n  const turns: TideTurn[] = [];\n  const n = readings.length;\n  if (n < 3) return turns;\n\n  let i = 1;\n  while (i < n - 1) {\n    const cur = readings[i];\n    const prev = readings[i - 1];\n\n    let nextDiff = undefined;\n    for (let j = i + 1; j < n; j++) {\n      if (readings[j].height !== cur.height) {\n        nextDiff = readings[j];\n        break;\n      }\n    }\n\n    if (nextDiff !== undefined) {\n      if (cur.height > prev.height && cur.height > nextDiff.height) {\n        turns.push({ kind: \"high\", hour: cur.hour, height: cur.height });\n      } else if (cur.height < prev.height && cur.height < nextDiff.height) {\n        turns.push({ kind: \"low\", hour: cur.hour, height: cur.height });\n      }\n    }\n\n    while (i + 1 < n - 1 && readings[i + 1].height === cur.height) {\n      i++;\n    }\n    i++;\n  }\n\n  return turns;\n}",
        "test_cases": [
            {
                "input": {
                    "readings": [
                        {"hour": 0, "height": 2.0},
                        {"hour": 1, "height": 3.1},
                        {"hour": 2, "height": 3.5},
                        {"hour": 3, "height": 2.4},
                        {"hour": 4, "height": 1.0},
                        {"hour": 5, "height": 1.6},
                        {"hour": 6, "height": 2.2},
                        {"hour": 7, "height": 2.0},
                    ]
                },
                "expected": [
                    {"kind": "high", "hour": 2, "height": 3.5},
                    {"kind": "low", "hour": 4, "height": 1.0},
                    {"kind": "high", "hour": 6, "height": 2.2},
                ],
            },
            {
                "input": {
                    "readings": [
                        {"hour": 0, "height": 1.2},
                        {"hour": 1, "height": 1.8},
                        {"hour": 2, "height": 2.1},
                        {"hour": 3, "height": 2.1},
                        {"hour": 4, "height": 1.7},
                        {"hour": 5, "height": 1.0},
                        {"hour": 6, "height": 0.6},
                        {"hour": 7, "height": 0.9},
                        {"hour": 8, "height": 1.5},
                    ]
                },
                "expected": [
                    {"kind": "high", "hour": 2, "height": 2.1},
                    {"kind": "low", "hour": 6, "height": 0.6},
                ],
            },
        ],
        "time_complexity": "O(n)",
        "space_complexity": "O(k) where k is number of turns",
        "edge_cases": ["Water holds at peak for multiple hours (plateau)", "Hour 0 or last hour looks like peak/trough but must be excluded", "Strictly monotone sequence with no turns"],
    },
    {
        "card_type": "qa",
        "category": "Classes & Invariants",
        "difficulty": "Medium",
        "priority": 90,
        "tags": ["cpsc210", "lab5", "lab", "classes", "invariants", "dom", "requireElement"],
        "locator": "Lab05.1 — Lab 5: Watching the Tides — TASK T2: The Dashboard Class (Its constructor)",
        "quote": "Its job is the class's invariant: once a Dashboard exists, every element it needs exists. A page that breaks the contract is refused here, by requireElement's error, so no method ever has to check for a missing element.",
        "front": "Lab 5, T2: what invariant does the Dashboard constructor establish, and how is it enforced?",
        "back": "1. **The Invariant**: Once a `Dashboard` object exists, **every DOM element required by the Page Contract is guaranteed to exist**.\n2. **How enforced**: The constructor calls `requireElement(document, selector)` for each contract element (`#station`, `#previous-day`, `#next-day`, `#play`, `#turns`, `#message`, `#tides`). If any element is missing, `requireElement` immediately throws: `\"the page has no element matching <selector>\"`.\n3. **Benefit**: No method (`start`, `showDay`, `moveDay`, `togglePlay`) ever has to check for null/undefined DOM elements.",
    },
    {
        "card_type": "qa",
        "category": "DOM & Events",
        "difficulty": "Easy",
        "priority": 90,
        "tags": ["cpsc210", "lab5", "lab", "javascript", "typescript", "this-binding", "arrow-functions", "events"],
        "locator": "Lab05.1 — Lab 5: Watching the Tides — TASK T2: The Dashboard Class (The DOM in brief)",
        "quote": "The listeners in start() use arrow functions, which keep this pointing at the dashboard; a function handler would not. Keep that style for any listener you add.",
        "front": "Lab 5, T2: why must DOM event listeners attached inside `Dashboard.start()` use arrow functions rather than regular `function` handlers?",
        "back": "1. In JavaScript, a regular `function` handler invoked by the DOM browser event loop has its `this` bound to the **event target element** (the clicked `<button>` or `<select>`).\n2. An **arrow function** does not bind its own `this`; it inherits `this` lexically from the enclosing scope (`Dashboard.start()`).\n3. Using `() => { this.showDay(); }` ensures that `this` points to the **`Dashboard` instance**, allowing access to `this.day`, `this.chart`, `this.message`, and other methods.",
    },
    {
        "card_type": "qa",
        "category": "Async & Timers",
        "difficulty": "Medium",
        "priority": 90,
        "tags": ["cpsc210", "lab5", "lab", "timers", "setInterval", "cleanup", "ui-state"],
        "locator": "Lab05.1 — Lab 5: Watching the Tides — TASK T3: Play the Month",
        "quote": "The Play button plays the month: every 500 ms the page moves on to the next day... Instead of keeping the handle, keep a function that stops the month, in a field typed (() => void) | undefined. Pressing Play starts the interval and stores a function that clears it; pressing Pause calls that function and sets the field back to undefined.",
        "front": "Lab 5, T3: describe the design of `togglePlay()`. How is interval state stored, how is cleanup performed, and how do UI buttons react?",
        "back": "1. **State representation**: Stored in a field `stopPlaying: (() => void) | undefined`. It is `undefined` while paused, which is how the dashboard checks whether the month is playing.\n2. **Starting Play**: Button text changes to **\"Pause\"**, Previous & Next buttons are **disabled**, and `setInterval(..., 500)` starts. Instead of storing the numeric timer handle, store a cleanup closure in `this.stopPlaying = () => clearInterval(handle)`.\n3. **Pausing**: Call `this.stopPlaying()`, set `this.stopPlaying = undefined`, button text returns to **\"Play\"**, and Previous & Next buttons are re-enabled (`disabled = false`).",
    },
    {
        "card_type": "qa",
        "category": "Testing",
        "difficulty": "Medium",
        "priority": 90,
        "tags": ["cpsc210", "lab5", "lab", "testing", "vitest", "jsdom", "fake-timers", "mocks"],
        "locator": "Lab05.1 — Lab 5: Watching the Tides — test/dashboard.test.ts comments",
        "quote": "The first line of this file asks vitest to run it inside jsdom, a headless DOM... Chart.js draws on a canvas, which jsdom does not have, so the harness below replaces it with a stand-in... Waiting half a second for real in every test would make the suite slow, so the T3 tests fake the interval timers and move time on themselves, with vi.advanceTimersByTimeAsync(500).",
        "front": "Lab 5: how does `test/dashboard.test.ts` test DOM controls, Chart.js, and 500ms intervals without opening a real browser or slowing down the test suite?",
        "back": "1. **Headless DOM (`jsdom`)**: `// @vitest-environment jsdom` simulates browser `document`, elements, and event dispatch directly in Node.\n2. **Chart.js Mock**: Canvas drawing is unsupported in jsdom, so `vi.mock(\"chart.js/auto\")` substitutes a `FakeChart` that records passed `data` and `options`.\n3. **Fake Service**: `startFakeService` runs the backend in-process, wrapping it in a fake `fetch` that logs every requested relative URL.\n4. **Fake Timers**: `vi.useFakeTimers()` mocks `setInterval`. Tests advance time instantly using `await vi.advanceTimersByTimeAsync(500)` instead of waiting real milliseconds.",
    },
]


def write_json_files():
    # 1. Bare array (original shape)
    orig_path = LABS_DIR / "cpsc210_lab05_watching_the_tides.json"
    with open(orig_path, "w", encoding="utf-8") as f:
        json.dump(LAB05_CARDS, f, indent=2, ensure_ascii=False)
    log.info(f"Wrote original bare array: {orig_path} ({len(LAB05_CARDS)} cards)")

    # 2. Wrapped copy
    wrapped_path = LABS_DIR / "cpsc210_lab05_watching_the_tides_wrapped.json"
    wrapped_data = {
        "deck": "Lab05 - Watching the Tides",
        "priority": 90,
        "notes": LAB05_CARDS,
    }
    with open(wrapped_path, "w", encoding="utf-8") as f:
        json.dump(wrapped_data, f, indent=2, ensure_ascii=False)
    log.info(f"Wrote wrapped copy: {wrapped_path}")


async def import_lab05():
    write_json_files()

    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == USER_EMAIL))
        if user is None:
            raise RuntimeError(f"User {USER_EMAIL} not found")

        # Find "Labs" parent deck
        labs_parent = await db.scalar(
            select(Deck).where(
                Deck.user_id == user.id,
                Deck.name == "Labs",
            )
        )
        if labs_parent is None:
            raise RuntimeError("Parent deck 'Labs' not found")

        # Ensure "Lab05 - Watching the Tides" deck under Labs
        deck_name = "Lab05 - Watching the Tides"
        deck = await db.scalar(
            select(Deck).where(
                Deck.user_id == user.id,
                Deck.name == deck_name,
                Deck.parent_id == labs_parent.id,
            )
        )
        if deck is None:
            deck = Deck(
                user_id=user.id,
                name=deck_name,
                parent_id=labs_parent.id,
                default_priority=90,
                position=5,
                thematic_nature="Lab 5: Watching the Tides (Frontend, Chart.js, Dashboard class, and async event timers).",
                documentation="Browser frontend for the tide service from Labs 3 and 4: station picker, Chart.js line chart with moon phase title, high/low turn list, and play/pause month animation.",
            )
            db.add(deck)
            await db.flush()
            log.info(f"+ Created deck: '{deck_name}' (id={deck.id})")
        else:
            log.info(f"= Reusing deck: '{deck_name}' (id={deck.id})")

        # Ingest cards with deduplication
        existing_fronts_query = await db.execute(
            select(Note.field_values).join(Card, Card.note_id == Note.id).where(Card.deck_id == deck.id)
        )
        existing_fronts = {
            str(fv.get("Front", "") or fv.get("front", "")).strip()
            for (fv,) in existing_fronts_query.all()
            if fv
        }

        created = 0
        skipped = 0

        for item in LAB05_CARDS:
            front = (item.get("front") or item.get("title") or "").strip()
            back = (item.get("back") or "").strip()

            if front in existing_fronts:
                skipped += 1
                continue
            existing_fronts.add(front)

            is_code = item.get("card_type") == "code"
            field_values = {
                "Front": front,
                "Back": back,
            }
            for k in [
                "starter_code",
                "test_cases",
                "starter_tests",
                "time_complexity",
                "space_complexity",
                "edge_cases",
                "title",
                "difficulty",
                "category",
                "language",
                "card_type",
            ]:
                if item.get(k) is not None:
                    field_values[k] = item[k]

            profile = "math_code" if is_code else "short_answer"
            nt = await default_note_type(db, user, "basic", grading_profile=profile)
            note = Note(user_id=user.id, note_type_id=nt.id, field_values=field_values)
            db.add(note)
            await db.flush()

            tags = list(item.get("tags") or [])
            if is_code:
                if "code" not in tags:
                    tags.append("code")
                if item.get("difficulty") and item.get("difficulty") not in tags:
                    tags.append(item["difficulty"])
                if item.get("category") and item.get("category") not in tags:
                    tags.append(item["category"])

            cards = await sync_cards(
                db, note, nt, deck.id, tags=tags, priority=item.get("priority", 90), origin="manual"
            )
            created += len(cards)

            quote = (item.get("quote") or "").strip()
            if quote:
                for card in cards:
                    db.add(
                        CardReference(
                            card_id=card.id,
                            quote=quote,
                            quote_verified=True,
                            locator=item.get("locator"),
                            source_title=item.get("source_title") or deck.name,
                        )
                    )

        # Record import history
        db.add(
            Import(
                user_id=user.id,
                filename="cpsc210_lab05_watching_the_tides",
                notes_mapped=created,
                cards_mapped=created,
                warnings=[],
            )
        )
        await db.commit()
        log.info(f"Import finished: {created} created, {skipped} skipped.")

        # Verify live API
        token = create_access_token(user.id)
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            resp = await client.get("/api/decks", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            decks_list = resp.json()
            d5 = next((d for d in decks_list if d["name"] == deck_name), None)
            assert d5 is not None, f"Deck {deck_name} not found in live API"
            root_deck = next((d for d in decks_list if d["name"] == "CPSC 210"), None)
            log.info(f"Verified live API: '{deck_name}' card_count={d5.get('card_count')}, root total_card_count={root_deck.get('total_card_count')}")


if __name__ == "__main__":
    asyncio.run(import_lab05())
