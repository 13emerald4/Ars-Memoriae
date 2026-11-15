import json
import os
import sys
import sqlite3

sys.stdout.reconfigure(encoding="utf-8")

USER_EMAIL = "michael.r.polley@outlook.com"
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "dev.db")

print(f"Connecting to database at {os.path.abspath(DB_PATH)}")
conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON;")
c = conn.cursor()

c.execute("SELECT id FROM users WHERE email = ?", (USER_EMAIL,))
user_row = c.fetchone()
if not user_row:
    raise RuntimeError(f"User {USER_EMAIL} not found!")
uid = user_row[0]
print(f"User ID: {uid}")

# Verify initial card count
c.execute("SELECT count(*) FROM cards c JOIN notes n ON c.note_id = n.id WHERE n.user_id = ?", (uid,))
initial_count = c.fetchone()[0]
print(f"Initial card count: {initial_count}")
if initial_count != 811:
    raise RuntimeError(f"Expected 811 cards, found {initial_count}!")

# Step 3: Unify Parent Decks and Set Positions & Priorities

# 1. Root Deck
ROOT_ID = "0556a75569624bbd971d71f858bbaab9"
c.execute("UPDATE decks SET position = 0, default_priority = 100 WHERE id = ?", (ROOT_ID,))

# 2. Basics Deck
BASICS_ID = "406b30f1c16c4b06a0828140293121f4"
c.execute("UPDATE decks SET position = 1, default_priority = 100 WHERE id = ?", (BASICS_ID,))
c.execute("UPDATE cards SET priority = 100 WHERE deck_id = ?", (BASICS_ID,))

# 3. Final Exam Prep Deck & Subdecks
FINAL_PREP_PARENT_ID = "062be5b306ba4f75bf0391310c94fc3c"
c.execute("UPDATE decks SET position = 2, default_priority = 90 WHERE id = ?", (FINAL_PREP_PARENT_ID,))

FP1_NAME = "Final Prep 1 - Making Code Correct (Ch 3, 4, 7, 8, 9)"
FP2_NAME = "Final Prep 2 - Building Abstractions (Ch 11-16)"
FP3_NAME = "Final Prep 3 - Growing Systems (Ch 17-22)"

c.execute("SELECT id FROM decks WHERE name = ? AND parent_id = ?", (FP1_NAME, FINAL_PREP_PARENT_ID))
fp1_id = c.fetchone()[0]
c.execute("SELECT id FROM decks WHERE name = ? AND parent_id = ?", (FP2_NAME, FINAL_PREP_PARENT_ID))
fp2_id = c.fetchone()[0]
c.execute("SELECT id FROM decks WHERE name = ? AND parent_id = ?", (FP3_NAME, FINAL_PREP_PARENT_ID))
fp3_id = c.fetchone()[0]

c.execute("UPDATE decks SET position = 1, default_priority = 90 WHERE id = ?", (fp1_id,))
c.execute("UPDATE cards SET priority = 90 WHERE deck_id = ?", (fp1_id,))

c.execute("UPDATE decks SET position = 2, default_priority = 80 WHERE id = ?", (fp2_id,))
c.execute("UPDATE cards SET priority = 80 WHERE deck_id = ?", (fp2_id,))

c.execute("UPDATE decks SET position = 3, default_priority = 70 WHERE id = ?", (fp3_id,))
c.execute("UPDATE cards SET priority = 70 WHERE deck_id = ?", (fp3_id,))

# 4. Part 1: Foundations (Canonical: 51e040a5cc2e..., Duplicate: e347ff6a13e4...)
CANON_P1_ID = "51e040a5cc2e43d79f7cdc76621dec0b"
DUP_P1_ID = "e347ff6a13e443879aa7f52cb57deae4"

c.execute("UPDATE decks SET position = 3, default_priority = 65 WHERE id = ?", (CANON_P1_ID,))

# Re-parent Ch 08 and Ch 09 to canonical P1
c.execute("UPDATE decks SET parent_id = ? WHERE parent_id = ?", (CANON_P1_ID, DUP_P1_ID))

# Delete duplicate P1 knowledge node & deck
c.execute("DELETE FROM knowledge_nodes WHERE deck_id = ?", (DUP_P1_ID,))
c.execute("DELETE FROM decks WHERE id = ?", (DUP_P1_ID,))

# Set priorities and positions for Ch 01 - Ch 09 under CANON_P1_ID
p1_subdecks_order = [
    ("Ch 01: Learning a New Language", 65, 1),
    ("Ch 02: Modelling With Types", 65, 2),
    ("Ch 05: Arrays and Iteration", 65, 3),
    ("Ch 03: Checking Invariants", 55, 4),
    ("Ch 04: Maintaining Invariants", 55, 5),
    ("Ch 06: Mutation and Side Effects", 55, 6),
    ("Ch 07: Asynchronous Effects", 55, 7),
    ("Ch 08: Designing for Failure", 55, 8),
    ("Ch 09: Validating Behaviour", 55, 9),
]

for name, prio, pos in p1_subdecks_order:
    c.execute("SELECT id FROM decks WHERE name = ? AND parent_id = ?", (name, CANON_P1_ID))
    row = c.fetchone()
    if row:
        did = row[0]
        c.execute("UPDATE decks SET position = ?, default_priority = ? WHERE id = ?", (pos, prio, did))
        c.execute("UPDATE cards SET priority = ? WHERE deck_id = ?", (prio, did))
    else:
        print(f"Warning: subdeck {name} not found under Part 1")

# The direct cards in canonical Part 1 (piazza cards): set to 55
c.execute("UPDATE cards SET priority = 55 WHERE deck_id = ?", (CANON_P1_ID,))

# 5. Lecture Activities (Canonical: ca8a2455..., Duplicate: d40978d7...)
CANON_LA_ID = "ca8a24554b8b465eaa54203173ca02d3"
DUP_LA_ID = "d40978d7055f48f8893b0831bd6a2072"

c.execute("UPDATE decks SET position = 4, default_priority = 45 WHERE id = ?", (CANON_LA_ID,))

# Merge LA08: duplicate 91636856dc3145918bb379136e29c3c6 -> canonical 3c3cc84a52594cf6afbe91249e69229c
CANON_LA08_ID = "3c3cc84a52594cf6afbe91249e69229c"
DUP_LA08_ID = "91636856dc3145918bb379136e29c3c6"
c.execute("UPDATE cards SET deck_id = ? WHERE deck_id = ?", (CANON_LA08_ID, DUP_LA08_ID))

# Merge LA09: duplicate 38b663363349401cbad68599b1115e1a -> canonical 2f1a61a4af6b4c258b7397cd084f8050
CANON_LA09_ID = "2f1a61a4af6b4c258b7397cd084f8050"
DUP_LA09_ID = "38b663363349401cbad68599b1115e1a"
c.execute("UPDATE cards SET deck_id = ? WHERE deck_id = ?", (CANON_LA09_ID, DUP_LA09_ID))

# Re-parent LA10, LA11, LA12 under CANON_LA_ID
c.execute("UPDATE decks SET parent_id = ? WHERE parent_id = ? AND name IN ('LA10', 'LA11', 'LA12')", (CANON_LA_ID, DUP_LA_ID))

# Delete empty child decks and duplicate LA parent
c.execute("SELECT id FROM decks WHERE parent_id = ?", (DUP_LA_ID,))
dup_la_kids = [r[0] for r in c.fetchall()]
for kid_id in dup_la_kids:
    c.execute("DELETE FROM knowledge_nodes WHERE deck_id = ?", (kid_id,))
    c.execute("DELETE FROM decks WHERE id = ?", (kid_id,))
c.execute("DELETE FROM knowledge_nodes WHERE deck_id = ?", (DUP_LA_ID,))
c.execute("DELETE FROM decks WHERE id = ?", (DUP_LA_ID,))

# Set position and priority on all LA subdecks LA01..LA12
for i in range(1, 13):
    la_name = f"LA{i:02d}"
    c.execute("SELECT id FROM decks WHERE name = ? AND parent_id = ?", (la_name, CANON_LA_ID))
    row = c.fetchone()
    if row:
        did = row[0]
        c.execute("UPDATE decks SET position = ?, default_priority = 45 WHERE id = ?", (i, did))
        c.execute("UPDATE cards SET priority = 45 WHERE deck_id = ?", (did,))

# 6. Midterm 3 (Canonical: df6a2dc4..., Duplicate: 8f4d81a6...)
CANON_MT3_ID = "df6a2dc45bc543ffb2144ed7712a961e"
DUP_MT3_ID = "8f4d81a682494c26ae61d83aff8eea8c"

c.execute("UPDATE decks SET name = 'Midterm 3', position = 5, default_priority = 35 WHERE id = ?", (CANON_MT3_ID,))

# Re-parent MT3 - Practice Midterm and CPSC 210 MT3 Essentials to CANON_MT3_ID
c.execute("UPDATE decks SET parent_id = ? WHERE parent_id = ?", (CANON_MT3_ID, DUP_MT3_ID))
c.execute("DELETE FROM knowledge_nodes WHERE deck_id = ?", (DUP_MT3_ID,))
c.execute("DELETE FROM decks WHERE id = ?", (DUP_MT3_ID,))

# Set priority 35 for all MT3 subdecks and cards
def update_tree_priority(parent_id, prio):
    c.execute("SELECT id FROM decks WHERE parent_id = ?", (parent_id,))
    kids = [r[0] for r in c.fetchall()]
    for kid in kids:
        c.execute("UPDATE decks SET default_priority = ? WHERE id = ?", (prio, kid))
        c.execute("UPDATE cards SET priority = ? WHERE deck_id = ?", (prio, kid))
        update_tree_priority(kid, prio)

c.execute("UPDATE cards SET priority = 35 WHERE deck_id = ?", (CANON_MT3_ID,))
update_tree_priority(CANON_MT3_ID, 35)

# 7. Labs (Canonical: 7549efe5..., Duplicate: 90191949...)
CANON_LABS_ID = "7549efe56f5c4dc7b4fb3e9fbfecf4a6"
DUP_LABS_ID = "9019194922e64c12bbcee8e2faae5647"

c.execute("UPDATE decks SET position = 6, default_priority = 15 WHERE id = ?", (CANON_LABS_ID,))

# Re-parent Lab05 to CANON_LABS_ID
c.execute("UPDATE decks SET parent_id = ? WHERE parent_id = ? AND name LIKE 'Lab05%'", (CANON_LABS_ID, DUP_LABS_ID))

# Delete empty child decks under DUP_LABS_ID and delete duplicate parent
c.execute("SELECT id FROM decks WHERE parent_id = ?", (DUP_LABS_ID,))
dup_lab_kids = [r[0] for r in c.fetchall()]
for kid_id in dup_lab_kids:
    c.execute("DELETE FROM knowledge_nodes WHERE deck_id = ?", (kid_id,))
    c.execute("DELETE FROM decks WHERE id = ?", (kid_id,))
c.execute("DELETE FROM knowledge_nodes WHERE deck_id = ?", (DUP_LABS_ID,))
c.execute("DELETE FROM decks WHERE id = ?", (DUP_LABS_ID,))

# Order Lab01..Lab05
c.execute("SELECT id, name FROM decks WHERE parent_id = ? ORDER BY name", (CANON_LABS_ID,))
for idx, (lid, lname) in enumerate(c.fetchall()):
    c.execute("UPDATE decks SET position = ?, default_priority = 15 WHERE id = ?", (idx + 1, lid))
    c.execute("UPDATE cards SET priority = 15 WHERE deck_id = ?", (lid,))

# 8. Clean ! Part 2 & ! Part 3
DUP_P2_ID = "2157b7a5d986488993aedf8f27867564"
CANON_P2_ID = "8c492dc6cca04d848d4012f1fbbd9cb2"
c.execute("UPDATE decks SET position = 7, default_priority = 35 WHERE id = ?", (CANON_P2_ID,))
c.execute("DELETE FROM knowledge_nodes WHERE deck_id = ?", (DUP_P2_ID,))
c.execute("DELETE FROM decks WHERE id = ?", (DUP_P2_ID,))

DUP_P3_ID = "186fc8b36b7b44ed807483f01ad4312f"
CANON_P3_ID = "1b994e850af548379ccc28045c3145df"
c.execute("UPDATE decks SET position = 8, default_priority = 35 WHERE id = ?", (CANON_P3_ID,))
c.execute("DELETE FROM knowledge_nodes WHERE deck_id = ?", (DUP_P3_ID,))
c.execute("DELETE FROM decks WHERE id = ?", (DUP_P3_ID,))

# Step 4: Card Positions inside Basics and Final Prep 1/2/3

def assign_card_positions(deck_id, json_path):
    d = json.load(open(json_path, encoding="utf-8"))
    items = d if isinstance(d, list) else d.get("cards", [])
    c.execute("SELECT c.id, n.field_values FROM cards c JOIN notes n ON c.note_id = n.id WHERE c.deck_id = ?", (deck_id,))
    db_cards = c.fetchall()
    matched_ids = set()
    for idx, item in enumerate(items):
        target_title = item.get("title", "").strip()
        target_front = item.get("front", "").strip()
        matched_card_id = None
        for cid, fv_str in db_cards:
            if cid in matched_ids:
                continue
            fv = json.loads(fv_str)
            db_title = fv.get("title", "").strip()
            db_front = (fv.get("Front") or fv.get("front") or "").strip()
            if (target_title and target_title == db_title) or (target_front and target_front[:50] == db_front[:50]):
                matched_card_id = cid
                break
        if matched_card_id:
            c.execute("UPDATE cards SET position = ? WHERE id = ?", (idx, matched_card_id))
            matched_ids.add(matched_card_id)
        else:
            print(f"Warning: unmatched card {idx} '{target_title}' in {json_path}")
    print(f"Assigned positions to {len(matched_ids)}/{len(items)} cards in deck {deck_id}")

print("Assigning intra-deck positions...")
assign_card_positions(BASICS_ID, r"C:\Users\micha\OneDrive\Documents\UBC BCS ICS\CPSC 210\06 Flashcards\7 - Basics\cpsc210_basics_foundations.json")
assign_card_positions(fp1_id, r"C:\Users\micha\OneDrive\Documents\UBC BCS ICS\CPSC 210\06 Flashcards\8 - Final\cpsc210_final_p1_making_code_correct.json")
assign_card_positions(fp2_id, r"C:\Users\micha\OneDrive\Documents\UBC BCS ICS\CPSC 210\06 Flashcards\8 - Final\cpsc210_final_p2_building_abstractions.json")
assign_card_positions(fp3_id, r"C:\Users\micha\OneDrive\Documents\UBC BCS ICS\CPSC 210\06 Flashcards\8 - Final\cpsc210_final_p3_growing_systems.json")

# Sync Knowledge Nodes with Decks
c.execute("SELECT id, name, parent_id, position, default_priority FROM decks WHERE user_id = ?", (uid,))
all_decks = c.fetchall()

# Map deck_id to node_id
deck_to_node = {}
c.execute("SELECT id, deck_id FROM knowledge_nodes WHERE user_id = ? AND deck_id IS NOT NULL", (uid,))
for nid, did in c.fetchall():
    deck_to_node[did] = nid

# Update existing knowledge nodes
for did, dname, parent_deck_id, pos, prio in all_decks:
    if did in deck_to_node:
        parent_node_id = deck_to_node.get(parent_deck_id) if parent_deck_id else None
        c.execute("""
            UPDATE knowledge_nodes
            SET title = ?, parent_id = ?, position = ?, priority = ?
            WHERE id = ?
        """, (dname, parent_node_id, pos, prio, deck_to_node[did]))
    else:
        # Create missing node
        import uuid as _u
        new_nid = _u.uuid4().hex
        parent_node_id = deck_to_node.get(parent_deck_id) if parent_deck_id else None
        c.execute("""
            INSERT INTO knowledge_nodes (id, user_id, parent_id, kind, title, position, priority, deck_id)
            VALUES (?, ?, ?, 'deck', ?, ?, ?, ?)
        """, (new_nid, uid, parent_node_id, dname, pos, prio, did))
        deck_to_node[did] = new_nid

conn.commit()

# Final Verification
c.execute("SELECT count(*) FROM cards c JOIN notes n ON c.note_id = n.id WHERE n.user_id = ?", (uid,))
final_count = c.fetchone()[0]
print(f"\nFinal Card Count: {final_count} (must equal {initial_count})")
assert final_count == 811, f"Mismatch: {final_count} != 811"

# Check duplicates across the entire collection
c.execute("""
    SELECT json_extract(n.field_values, '$.title') as t,
           coalesce(json_extract(n.field_values, '$.Front'), json_extract(n.field_values, '$.front')) as f,
           count(*)
    FROM cards c
    JOIN notes n ON c.note_id = n.id
    WHERE n.user_id = ?
    GROUP BY t, f
    HAVING count(*) > 1
""", (uid,))
dups = c.fetchall()
print(f"Duplicate (title, front) pairs: {len(dups)}")
assert len(dups) == 0, f"Found duplicates: {dups}"

conn.close()
print("Database repair and ordering complete successfully!")
