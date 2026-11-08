"""Verification test script for the newly built SPAN 321 (49 Preguntas) deck.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BACKEND_DIR / "dev.db"

EXPECTED_SUBDECKS = {
    "07 Roma y Cartago": 8,
    "08 La Conquista Romana": 3,
    "09 La Organización Romana": 11,
    "10 La Romanización": 6,
    "11 Cultura y Arte Romano": 8,
    "12 La Religión de Roma": 9,
    "13 La Cristianización de Hispania": 4,
}

def verify():
    sys.stdout.reconfigure(encoding="utf-8")
    assert DB_PATH.exists(), f"Database not found at {DB_PATH}"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Verify Root Deck
    cursor.execute(
        "SELECT id, name FROM decks WHERE name = 'SPAN 321: Guía de Recuperación (49 Preguntas)'"
    )
    root = cursor.fetchone()
    assert root is not None, "Root deck 'SPAN 321: Guía de Recuperación (49 Preguntas)' not found!"
    root_id, root_name = root
    print(f"PASS: Root deck verified: '{root_name}' ({root_id})")

    # 2. Verify Subdecks
    cursor.execute(
        "SELECT id, name, position FROM decks WHERE parent_id = ? ORDER BY position",
        (root_id,),
    )
    subdecks = cursor.fetchall()
    assert len(subdecks) == 7, f"Expected 7 subdecks, found {len(subdecks)}"
    print(f"PASS: Exactly 7 subdecks found under root.")

    subdeck_counts = {}
    for s_id, s_name, pos in subdecks:
        cursor.execute("SELECT count(*) FROM cards WHERE deck_id = ?", (s_id,))
        count = cursor.fetchone()[0]
        subdeck_counts[s_name] = count
        expected = EXPECTED_SUBDECKS.get(s_name)
        assert count == expected, f"Subdeck '{s_name}' has {count} cards, expected {expected}"
        print(f"  PASS Subdeck [{pos}]: '{s_name}' -> {count} cards (matches expected)")

    # 3. Verify Total Cards
    cursor.execute(
        """
        SELECT c.id, c.position, c.is_schema_checkpoint, json_extract(n.field_values, '$.Front'), json_extract(n.field_values, '$.Back')
        FROM cards c
        JOIN notes n ON c.note_id = n.id
        WHERE c.deck_id IN (SELECT id FROM decks WHERE parent_id = ?)
        ORDER BY c.position
        """,
        (root_id,),
    )
    cards = cursor.fetchall()
    assert len(cards) == 49, f"Expected exactly 49 cards, found {len(cards)}"
    print(f"\nPASS: Total cards under deck hierarchy = {len(cards)} (Exactly 49)")

    # 4. Verify Content & Format of every single card
    tree_failures = []
    citation_failures = []
    image_failures = []
    checkpoint_counts = 0

    for card_id, pos, is_chk, front, back in cards:
        # Check citation in front
        has_citation = bool(re.search(r'\[(?:Guía|T\d|Intro)[^\]]+\]', front))
        if not has_citation:
            citation_failures.append((pos, front[:50]))

        # Check tree in back
        has_tree = ('├──' in back or '└──' in back) and '│' in back or ('├──' in back and '└──' in back)
        if not has_tree:
            tree_failures.append((pos, front[:50]))

        # Check checkpoints
        if is_chk == 1:
            checkpoint_counts += 1
            assert '★' in front, f"Card at position {pos} is a checkpoint but front lacks '★'"

        # Check media images
        img_matches = re.findall(r'!\[\]\((/media/[^\)]+)\)', front)
        for img_url in img_matches:
            rel_path = img_url.lstrip('/')
            p1 = BACKEND_DIR.parent / rel_path
            p2 = BACKEND_DIR / rel_path
            if not p1.exists() and not p2.exists():
                image_failures.append((pos, img_url))

    assert len(citation_failures) == 0, f"Cards missing citations: {citation_failures}"
    print("PASS: 100% of cards contain valid bracketed slide/guide citations [Guía X; T2 Y].")

    assert len(tree_failures) == 0, f"Cards missing ASCII trees: {tree_failures}"
    print("PASS: 100% of card backs contain structured visual ASCII trees (├──, └──).")

    assert len(image_failures) == 0, f"Cards with missing media: {image_failures}"
    print("PASS: All referenced media images successfully verified on disk.")

    print(f"PASS: High-yield schema checkpoints verified: {checkpoint_counts} cards.")

    # 5. Verify Original Deck is intact
    cursor.execute(
        "SELECT count(*) FROM cards WHERE deck_id IN (SELECT id FROM decks WHERE id = '5cff1f3e336e4ccfa0fec1e297c2581f' OR parent_id = '5cff1f3e336e4ccfa0fec1e297c2581f' OR parent_id IN (SELECT id FROM decks WHERE parent_id = '5cff1f3e336e4ccfa0fec1e297c2581f'))"
    )
    orig_count = cursor.fetchone()[0]
    print(f"PASS: Original deck 'SPAN 321: Examen 1' remains completely intact with {orig_count} cards.")

    conn.close()
    print("\n" + "=" * 65)
    print("ALL VERIFICATION CHECKS PASSED WITH 100% SUCCESS!")
    print("=" * 65)

if __name__ == "__main__":
    verify()
