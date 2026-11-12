"""Verifies the imported CPSC 210 Practice Midterm 3 deck in dev.db."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BACKEND_DIR / "dev.db"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def verify():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Check Root Deck CPSC 210
    cursor.execute("SELECT id, name, parent_id FROM decks WHERE name = 'CPSC 210'")
    root = cursor.fetchone()
    assert root is not None, "CPSC 210 root deck not found"
    root_id = root[0]
    print(f"PASS: Root deck verified: '{root[1]}' ({root_id})")

    # 2. Check Midterm 3 parent deck
    cursor.execute("SELECT id, name, parent_id, default_priority, target_event_title FROM decks WHERE name = 'Midterm 3' AND parent_id = ?", (root_id,))
    mt3 = cursor.fetchone()
    assert mt3 is not None, "Midterm 3 deck not found under CPSC 210"
    mt3_id = mt3[0]
    print(f"PASS: Midterm 3 deck verified: '{mt3[1]}' ({mt3_id}) [prio={mt3[3]}, event={mt3[4]}]")

    # 3. Check Practice Midterm subdeck
    cursor.execute("SELECT id, name, parent_id, default_priority FROM decks WHERE name LIKE '%Practice Midterm%' AND parent_id = ?", (mt3_id,))
    practice = cursor.fetchone()
    assert practice is not None, "Practice Midterm deck not found under Midterm 3"
    practice_id = practice[0]
    print(f"PASS: Practice Midterm deck verified: '{practice[1]}' ({practice_id}) [prio={practice[3]}]")

    # 4. Check Cards
    cursor.execute(
        """
        SELECT c.id, n.field_values, c.priority, c.tags, cr.quote, cr.locator
        FROM cards c
        JOIN notes n ON c.note_id = n.id
        LEFT JOIN card_references cr ON cr.card_id = c.id
        WHERE c.deck_id = ?
        """,
        (practice_id,)
    )
    cards = cursor.fetchall()
    assert len(cards) == 7, f"Expected 7 cards, found {len(cards)}"
    print("PASS: Exactly 7 cards found in Practice Midterm deck.")

    for i, (cid, fv_str, prio, tags_str, quote, locator) in enumerate(cards, 1):
        fv = json.loads(fv_str)
        title = fv.get("title") or "Untitled"
        has_starter = bool(fv.get("starter_code"))
        tests_count = len(fv.get("test_cases") or [])
        print(f"  [{i}] Card {cid[:8]} | Prio {prio} | {title} | Starter: {has_starter} ({len(fv.get('starter_code', '') or '')} chars) | Tests: {tests_count} | Has Quote: {bool(quote)}")

    print("\n=======================================================")
    print("ALL VERIFICATION CHECKS PASSED FOR PRACTICE MIDTERM 3!")
    print("=======================================================")

if __name__ == "__main__":
    verify()
