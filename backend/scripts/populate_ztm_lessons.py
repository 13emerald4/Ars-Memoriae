"""Populates concise Socratic lessons and key points for all 105 JS/TS cards in dev.db."""

import json
import sqlite3
from datetime import datetime

from app.content.js_ts_course.lessons import LESSONS, get_socratic_lesson

con = sqlite3.connect('backend/dev.db')
cur = con.cursor()

# Fetch all cards with their id and tags
cur.execute("SELECT id, tags FROM cards")
rows = cur.fetchall()

updated = 0
inserted = 0

for card_id, tags_json in rows:
    try:
        tags = json.loads(tags_json) if tags_json else []
    except Exception:
        tags = []

    # Find card key from tags
    card_key = None
    for t in tags:
        if t in LESSONS:
            card_key = t
            break

    if not card_key:
        continue

    lesson_body, key_points = get_socratic_lesson(card_key)
    if not lesson_body:
        continue

    # Check if card_lesson already exists
    cur.execute("SELECT card_id FROM card_lessons WHERE card_id = ?", (card_id,))
    exists = cur.fetchone()

    now = datetime.utcnow().isoformat()
    if exists:
        cur.execute(
            "UPDATE card_lessons SET body = ?, key_points = ?, model_used = ? WHERE card_id = ?",
            (lesson_body, json.dumps(key_points), "socratic-curriculum", card_id)
        )
        updated += 1
    else:
        cur.execute(
            "INSERT INTO card_lessons (card_id, body, key_points, model_used, created_at) VALUES (?, ?, ?, ?, ?)",
            (card_id, lesson_body, json.dumps(key_points), "socratic-curriculum", now)
        )
        inserted += 1

con.commit()
print(f"Done. Inserted {inserted} lessons, updated {updated} lessons.")

# Verify total in card_lessons
cur.execute("SELECT count(*) FROM card_lessons")
total = cur.fetchone()[0]
print(f"Total rows in card_lessons now: {total}")

con.close()
