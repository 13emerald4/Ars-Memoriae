import json
import sqlite3
from pathlib import Path

DEST_DIR = Path(r"C:\Users\micha\OneDrive\Documents\UBC BCS ICS\CPSC 210\Cards\Cards")
DEST_DIR.mkdir(parents=True, exist_ok=True)
backup_file = DEST_DIR / "cpsc210_all_481_cards_master_backup.json"

conn = sqlite3.connect("dev.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Fetch user
c.execute("SELECT id, email FROM users WHERE email = 'michael.r.polley@outlook.com'")
user = c.fetchone()
if not user:
    print("User not found!")
    exit(1)

user_id = user["id"]

# Fetch decks
c.execute("""
    SELECT d.id, d.name, d.parent_id, d.documentation, d.thematic_nature, d.source_documents
    FROM decks d
    WHERE d.user_id = ?
    ORDER BY d.name
""", (user_id,))
decks = [dict(row) for row in c.fetchall()]

# Fetch all cards with notes & references
c.execute("""
    SELECT c.id, c.note_id, c.deck_id, d.name as deck_name, n.field_values, c.state, c.stability, c.difficulty, c.due, c.tags, c.documentation as card_documentation
    FROM cards c
    JOIN decks d ON c.deck_id = d.id
    JOIN notes n ON c.note_id = n.id
    WHERE n.user_id = ?
    ORDER BY d.name, c.id
""", (user_id,))
cards_rows = c.fetchall()

cards_data = []
for row in cards_rows:
    card_dict = dict(row)
    try:
        card_dict["field_values"] = json.loads(card_dict["field_values"])
    except Exception:
        pass

    c.execute("""
        SELECT source_title, locator, quote, quote_verified
        FROM card_references
        WHERE card_id = ?
    """, (card_dict["id"],))
    refs = [dict(ref_row) for ref_row in c.fetchall()]
    card_dict["references"] = refs
    cards_data.append(card_dict)

master_backup = {
    "total_cards": len(cards_data),
    "user_email": user["email"],
    "exported_at": "2026-10-13",
    "decks": decks,
    "cards": cards_data
}

with open(backup_file, "w", encoding="utf-8") as f:
    json.dump(master_backup, f, indent=2, ensure_ascii=False)

print(f"Exported master backup of {len(cards_data)} cards to {backup_file}")
conn.close()
