"""Builds the standalone 'SPAN 321: Guía de Recuperación (49 Preguntas)' deck in Ars Memoriae (dev.db).

Creates:
- 1 Root Deck: 'SPAN 321: Guía de Recuperación (49 Preguntas)'
- 7 Subdecks (07 to 13)
- 49 Notes and 49 Cards, each containing exact official Q&A prose, slide citations, and structured ASCII trees.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BACKEND_DIR / "dev.db"
DATA_FILE = BACKEND_DIR / "data" / "span321_49_questions.json"

USER_ID = "3e12b0d72e0e4d878e1b091bdaa3caa2"
NOTE_TYPE_ID = "37f2bad06d094459907f7707d9ddd7b4"
ROOT_DECK_NAME = "SPAN 321: Guía de Recuperación (49 Preguntas)"

SUBDECKS_ORDER = [
    "07 Roma y Cartago",
    "08 La Conquista Romana",
    "09 La Organización Romana",
    "10 La Romanización",
    "11 Cultura y Arte Romano",
    "12 La Religión de Roma",
    "13 La Cristianización de Hispania",
]

def make_uuid() -> str:
    return uuid.uuid4().hex

def build_deck():
    sys.stdout.reconfigure(encoding="utf-8")
    if not DB_PATH.exists():
        print(f"Error: Database {DB_PATH} not found.")
        sys.exit(1)
    if not DATA_FILE.exists():
        print(f"Error: Data file {DATA_FILE} not found.")
        sys.exit(1)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        cards_data = json.load(f)

    print(f"Connecting to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Check if root deck already exists
    cursor.execute("SELECT id FROM decks WHERE name = ? AND user_id = ?", (ROOT_DECK_NAME, USER_ID))
    existing_root = cursor.fetchone()
    if existing_root:
        root_deck_id = existing_root[0]
        print(f"Found existing root deck: {root_deck_id}. Purging old cards/subdecks under it for a clean build...")
        # Get all subdeck IDs
        cursor.execute("SELECT id FROM decks WHERE parent_id = ?", (root_deck_id,))
        old_subdecks = [r[0] for r in cursor.fetchall()]
        all_deck_ids = old_subdecks + [root_deck_id]

        for did in all_deck_ids:
            cursor.execute("SELECT note_id FROM cards WHERE deck_id = ?", (did,))
            note_ids = [r[0] for r in cursor.fetchall()]
            cursor.execute("DELETE FROM cards WHERE deck_id = ?", (did,))
            for nid in note_ids:
                cursor.execute("DELETE FROM notes WHERE id = ?", (nid,))
            if did != root_deck_id:
                cursor.execute("DELETE FROM decks WHERE id = ?", (did,))
    else:
        root_deck_id = make_uuid()
        cursor.execute(
            """
            INSERT INTO decks (
                id, user_id, parent_id, name, default_priority, created_at,
                documentation, thematic_nature, source_documents, position
            ) VALUES (?, ?, NULL, ?, 50, ?, ?, ?, '[]', 0)
            """,
            (
                root_deck_id,
                USER_ID,
                ROOT_DECK_NAME,
                now_iso,
                "Mazo exclusivo con las 49 preguntas de la Parte II de la Guía de Recuperación y Examen 1 (Secciones 7 a 13) de SPAN 321 (Prof. Marisol). Formato canónico con citas PPT y árboles de retención conceptual.",
                "Historia, Cultura y Civilización Romana en Hispania",
            ),
        )
        print(f"Created Root Deck '{ROOT_DECK_NAME}' (ID: {root_deck_id})")

    # 2. Create the 7 Subdecks
    subdeck_ids: dict[str, str] = {}
    for pos, sname in enumerate(SUBDECKS_ORDER, start=1):
        s_id = make_uuid()
        subdeck_ids[sname] = s_id
        cursor.execute(
            """
            INSERT INTO decks (
                id, user_id, parent_id, name, default_priority, created_at,
                documentation, thematic_nature, source_documents, position
            ) VALUES (?, ?, ?, ?, 50, ?, ?, ?, '[]', ?)
            """,
            (
                s_id,
                USER_ID,
                root_deck_id,
                sname,
                now_iso,
                f"Submazo temático correspondiente a la sección {sname} del documento maestro de recuperación de SPAN 321.",
                "Historia y Cultura Romana",
                pos,
            ),
        )
        print(f"  Created Subdeck [{pos}]: '{sname}' (ID: {s_id})")

    # 3. Insert Notes and Cards
    inserted_cards = 0
    star_cards = 0

    for card_info in cards_data:
        q_num = card_info["num"]
        sec_name = card_info["section"]
        is_star = card_info["star"]
        front_text = card_info["front"]
        back_text = card_info["back"]
        img_url = card_info.get("image")

        target_deck_id = subdeck_ids[sec_name]

        # Embed image markdown on front if provided and not already present
        if img_url and img_url not in front_text:
            front_text = f"{front_text}\n\n![]({img_url})"

        note_id = make_uuid()
        card_id = make_uuid()

        field_values = {
            "Front": front_text,
            "Back": back_text,
        }
        field_values_json = json.dumps(field_values, ensure_ascii=False)
        tags_json = json.dumps(["span321", "recuperacion", "examen1", sec_name.split()[0]], ensure_ascii=False)

        # Insert Note
        cursor.execute(
            """
            INSERT INTO notes (id, user_id, note_type_id, field_values, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (note_id, USER_ID, NOTE_TYPE_ID, field_values_json, now_iso),
        )

        # Insert Card
        cursor.execute(
            """
            INSERT INTO cards (
                id, note_id, deck_id, template_slot, state,
                step, priority, origin, lapse_count, leech_flag,
                suspended, tags, active_weaknesses, weakness_history,
                source_documents, lexicon_glosses, position, is_schema_checkpoint
            ) VALUES (
                ?, ?, ?, 'default', 'new',
                0, 50, 'manual', 0, 0,
                0, ?, '[]', '[]',
                '[]', '[]', ?, ?
            )
            """,
            (
                card_id,
                note_id,
                target_deck_id,
                tags_json,
                q_num,
                1 if is_star else 0,
            ),
        )

        inserted_cards += 1
        if is_star:
            star_cards += 1

    conn.commit()
    conn.close()

    print("\n" + "=" * 65)
    print(f"SUCCESS: Dedicated deck '{ROOT_DECK_NAME}' built successfully!")
    print(f"Total Subdecks Created: {len(SUBDECKS_ORDER)}")
    print(f"Total Cards Created: {inserted_cards} (Expected: 49)")
    print(f"Total Starred High-Yield Cards (Checkpoints): {star_cards}")
    print("=" * 65)

if __name__ == "__main__":
    build_deck()
