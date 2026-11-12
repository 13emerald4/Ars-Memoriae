"""
Apply 3 priority levels (P1=85, P2=60, P3=35) across all 12 CPSC 210 subdecks.
Updates:
1. SQLite database (`backend/dev.db`): cards.priority, notes.tags, notes.field_values, decks.default_priority
2. OneDrive source JSON files in:
   - `1 - LA decks/` (LA01 to LA07)
   - `6 - Labs/` (Lab01 to Lab05) and their `_wrapped.json` counterparts
"""

import json
import os
import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

TIER_SCORES = {
    "P1": 85,
    "P2": 60,
    "P3": 35
}

MAPPING = {
    "LA01": {
        "P1": ["Implement `gradeToLetter"],
        "P2": ["signature AND body for `clamp", "Implement `percentage"],
        "P3": ["Write `gradeFromPoints"]
    },
    "LA02": {
        "P1": ["countItems"],
        "P2": ["totalDamage"],
        "P3": ["withoutConsumables", "strongestWeapon"]
    },
    "LA03": {
        "P1": ["withdraw returning a Result", "withdraw"],
        "P2": ["preconditions", "deposit"],
        "P3": ["addMonthlyInterest", "applyTransactions"]
    },
    "LA04": {
        "P1": ["enroll (fix the off-by-one)", "src/roster01.ts enroll"],
        "P2": ["makeSection"],
        "P3": ["removeFirst", "withEnrollment"]
    },
    "LA05": {
        "P1": ["Comfort model", "muggyHours", "peakHumidity(day"],
        "P2": ["firstComfortable", "freezingHourNumbers", "peakHumidityWhenFreezing"],
        "P3": ["coldestHour", "longestMuggyStreak", "hasCloseTemperatures"]
    },
    "LA06": {
        "P1": ["makeTask", "increaseWorkedHours", "setTaskStatus"],
        "P2": ["fileTasks", "Status Column Counts", "logOnBoard"],
        "P3": ["Standup Snapshot", "diffHoursWorked", "Closure Task with Private workedHours"]
    },
    "LA07": {
        "P1": ["readDay(files", "getDay(files"],
        "P2": ["A day's recording file", "matchPattern", "dayLabel"],
        "P3": ["listDaysBelow", "getAverage", "listMonths"]
    },
    "Lab01 - Reading the Tides": {
        "P1": ["makeReading(day, hour, height, phase)", "tideKind(phase)", "describeHeight(reading)"],
        "P2": ["swing(a, b)", "countOn(readings, day)", "write the JSDoc invariants block", "fail against the stub"],
        "P3": ["estimateHeight(high, low, hoursAfterHigh)", "estimateHeight` need `low`", "makeReading` tests the mutation"]
    },
    "Lab02 - Charting the Tides": {
        "P1": ["chronological(readings)`: a **new** array", "highestReading(readings)", "hoursAbove(readings, height)", "summariseDay(readings, day)"],
        "P2": ["extremeTides(readings, fromDay, toDay", "summariseMonth(readings)", "passageWindows(readings, minHeight", "not modify"],
        "P3": ["makeTideStation()", "station behaviours your suite", "small hand-built arrays", "derived operation"]
    },
    "Lab03 - Serving the Tides": {
        "P1": ["getLatest(request, service)", "parseReading(body, maxHeight)", "postReading(request, service)", "meaning of each status code"],
        "P2": ["getReadings(request, service)", "two rules hold for", "malformed POST body", "Number(\"abc\")"],
        "P3": ["list the `?day` tests", "write the POST tests a mutation grader wants", "to.equal` vs `to.deep.equal", "T0 (Write the Contract)", "existing station with"]
    },
    "Lab04 - Keeping the Tides": {
        "P1": ["getWindows(request, service)", "implement the core of `loadStation", "postReading` **persist**", "two **bold** (most important) goals"],
        "P2": ["getExtremes(request, service)", "await saveStation", "run every file entry", "no qualifying window is"],
        "P3": ["write the persistence tests", "extremeTides` already returns an error", "there's no stub", "DELETE endpoint"]
    },
    "Lab05 - Watching the Tides": {
        "P1": ["stationOptions(stations", "stepDay(day", "chartTitle(stationTitle", "invariant does the Dashboard constructor establish"],
        "P2": ["turnLabel(turn", "highsAndLows(readings", "what is the Page Contract", "why must DOM event listeners attached inside `Dashboard.start()"],
        "P3": ["togglePlay()", "what are the lab's main goals, and how does the code structure", "dashboard.test.ts` test DOM controls"]
    }
}

def determine_tier(deck_name: str, card_text: str) -> str:
    patterns = MAPPING.get(deck_name)
    if not patterns:
        raise ValueError(f"No patterns found for deck {deck_name}")
    for tier in ["P1", "P2", "P3"]:
        for p in patterns[tier]:
            if p.lower() in card_text.lower():
                return tier
    raise ValueError(f"No tier matched for deck '{deck_name}': {card_text[:80]}")

def update_database(db_path: str):
    print("=" * 60)
    print("1. UPDATING ARS-MEMORIAE DATABASE")
    print("=" * 60)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Get child decks under Lecture Activities and Labs
    cur.execute("""
        SELECT d.id, d.name, p.name
        FROM decks d
        JOIN decks p ON p.id = d.parent_id
        WHERE p.name IN ('Lecture Activities', 'Labs')
    """)
    child_decks = cur.fetchall()
    child_deck_map = {name: (did, parent) for did, name, parent in child_decks}

    # Set default priority = 60 on all 12 child decks
    for name, (did, _) in child_deck_map.items():
        cur.execute("UPDATE decks SET default_priority = 60 WHERE id = ?", (did,))
    print(f"Set default_priority = 60 on {len(child_deck_map)} child decks.")

    # Update cards and notes
    cur.execute("""
        SELECT card.id, n.id, d.name, n.field_values, n.tags
        FROM cards card
        JOIN decks d ON d.id = card.deck_id
        JOIN notes n ON n.id = card.note_id
        JOIN decks p ON p.id = d.parent_id
        WHERE p.name IN ('Lecture Activities', 'Labs')
    """)
    rows = cur.fetchall()

    tier_stats = {}
    for card_id, note_id, dname, fvals_str, tags_str in rows:
        fvals = json.loads(fvals_str)
        text = (fvals.get("title") or "") + " " + (fvals.get("Front") or "")
        tier = determine_tier(dname, text)
        score = TIER_SCORES[tier]

        # Update card priority
        cur.execute("UPDATE cards SET priority = ? WHERE id = ?", (score, card_id))

        # Update note tags
        try:
            tags = json.loads(tags_str) if tags_str else []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
        except Exception:
            tags = []
        tags = [t for t in tags if t not in ("P1", "P2", "P3")]
        tags.append(tier)
        cur.execute("UPDATE notes SET tags = ? WHERE id = ?", (json.dumps(tags), note_id))

        # Update note field_values
        fvals["priority"] = score
        fvals["priority_level"] = tier
        cur.execute("UPDATE notes SET field_values = ? WHERE id = ?", (json.dumps(fvals), note_id))

        tier_stats[dname] = tier_stats.get(dname, {"P1": 0, "P2": 0, "P3": 0})
        tier_stats[dname][tier] += 1

    conn.commit()
    conn.close()

    print(f"Updated {len(rows)} cards in dev.db:")
    for dname, stats in sorted(tier_stats.items()):
        print(f"  {dname:28} -> P1: {stats['P1']}, P2: {stats['P2']}, P3: {stats['P3']} (Total: {sum(stats.values())})")


def update_onedrive_files(base_path: str):
    print("\n" + "=" * 60)
    print("2. UPDATING ONEDRIVE JSON SOURCE FILES")
    print("=" * 60)

    la_dir = os.path.join(base_path, "1 - LA decks")
    lab_dir = os.path.join(base_path, "6 - Labs")

    # Update LA decks
    la_files = sorted([f for f in os.listdir(la_dir) if f.startswith("cpsc210_mt2_LA") and f.endswith(".json")])
    for fname in la_files:
        fpath = os.path.join(la_dir, fname)
        la_name = fname.split("_")[-1].replace(".json", "")
        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)

        notes = data.get("notes", [])
        for note in notes:
            text = (note.get("title") or "") + " " + (note.get("front") or "")
            tier = determine_tier(la_name, text)
            score = TIER_SCORES[tier]
            note["priority"] = score
            note["priority_level"] = tier
            tags = note.get("tags", [])
            tags = [t for t in tags if t not in ("P1", "P2", "P3")]
            tags.append(tier)
            note["tags"] = tags

        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  Updated LA deck: {fname} ({len(notes)} cards)")

    # Update Lab decks
    lab_files = [
        ("cpsc210_lab01_reading_the_tides.json", "Lab01 - Reading the Tides"),
        ("cpsc210_lab02_charting_the_tides.json", "Lab02 - Charting the Tides"),
        ("cpsc210_lab03_serving_the_tides.json", "Lab03 - Serving the Tides"),
        ("cpsc210_lab04_keeping_the_tides.json", "Lab04 - Keeping the Tides"),
        ("cpsc210_lab05_watching_the_tides.json", "Lab05 - Watching the Tides"),
    ]

    for fname, dname in lab_files:
        fpath = os.path.join(lab_dir, fname)
        with open(fpath, encoding="utf-8") as f:
            cards = json.load(f)

        for card in cards:
            text = (card.get("title") or "") + " " + (card.get("front") or "")
            tier = determine_tier(dname, text)
            score = TIER_SCORES[tier]
            card["priority"] = score
            card["priority_level"] = tier
            tags = card.get("tags", [])
            tags = [t for t in tags if t not in ("P1", "P2", "P3")]
            tags.append(tier)
            card["tags"] = tags

        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(cards, f, indent=2, ensure_ascii=False)

        # Update wrapped copy
        wrapped_fname = fname.replace(".json", "_wrapped.json")
        wrapped_fpath = os.path.join(lab_dir, wrapped_fname)
        if os.path.exists(wrapped_fpath):
            with open(wrapped_fpath, encoding="utf-8") as f:
                wrapped_data = json.load(f)
            wrapped_data["default_priority"] = 60
            wrapped_data["notes"] = cards
            with open(wrapped_fpath, "w", encoding="utf-8") as f:
                json.dump(wrapped_data, f, indent=2, ensure_ascii=False)

        print(f"  Updated Lab deck: {fname} and wrapped copy ({len(cards)} cards)")


if __name__ == "__main__":
    db_path = r"c:\Users\micha\Documents\antigravity\clever-rutherford\backend\dev.db"
    onedrive_base = r"C:\Users\micha\OneDrive\Documents\UBC BCS ICS\CPSC 210\06 Flashcards"
    update_database(db_path)
    update_onedrive_files(onedrive_base)
    print("\nAll subdeck cards successfully updated to P1, P2, P3 priorities!")
