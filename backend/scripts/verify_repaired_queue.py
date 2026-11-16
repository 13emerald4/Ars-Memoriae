import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.services.queue_service import fetch_new_candidates

USER_EMAIL = "michael.r.polley@outlook.com"

async def run_verification():
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == USER_EMAIL))
        if not user:
            print("User not found!")
            return

        print(f"=== VERIFYING REPAIRED QUEUE FOR {user.email} ===")

        # Check duplicate pairs
        import sqlite3
        conn = sqlite3.connect("dev.db")
        c = conn.cursor()
        c.execute("""
            SELECT count(*) FROM (
                SELECT json_extract(n.field_values, '$.title') as t,
                       coalesce(json_extract(n.field_values, '$.Front'), json_extract(n.field_values, '$.front')) as f
                FROM cards c
                JOIN notes n ON c.note_id = n.id
                WHERE n.user_id = ?
                GROUP BY t, f
                HAVING count(*) > 1
            )
        """, (user.id.hex,))
        dup_count = c.fetchone()[0]
        c.execute("SELECT count(*) FROM cards c JOIN notes n ON c.note_id = n.id WHERE n.user_id = ?", (user.id.hex,))
        total_card_count = c.fetchone()[0]
        conn.close()

        print(f"Total card count: {total_card_count}")
        print(f"Duplicate (title, front) pairs: {dup_count}")

        # Fetch top 60 new candidates through queue_service logic
        candidates = await fetch_new_candidates(db, user, limit=60)
        print(f"\n=== FIRST {len(candidates)} CARDS VIA fetch_new_candidates ===")
        for idx, card in enumerate(candidates, 1):
            fv = card.note.field_values or {}
            title = fv.get("title") or fv.get("Front") or fv.get("front") or ""
            deck_name = card.deck.name
            print(f"  {idx:2d}. [Prio {card.effective_priority:3d} | Pos {card.position!s:>4s}] [{deck_name[:32]}] {title[:45]}")

        # Priority distribution across all decks
        print("\n=== PRIORITY DISTRIBUTION ACROSS ALL DECKS ===")
        conn = sqlite3.connect("dev.db")
        c = conn.cursor()
        c.execute("""
            SELECT coalesce(c.priority, d.default_priority) as eff_prio,
                   d.name,
                   count(c.id)
            FROM cards c
            JOIN decks d ON c.deck_id = d.id
            JOIN notes n ON c.note_id = n.id
            WHERE n.user_id = ?
            GROUP BY eff_prio, d.name
            ORDER BY eff_prio DESC, d.position ASC, d.name ASC
        """, (user.id.hex,))
        rows = c.fetchall()
        for prio, dname, cnt in rows:
            print(f"  [Prio {prio:3d}] ({cnt:3d} cards) {dname}")

        print("\n=== OVERALL PRIORITY SUMMARY ===")
        c.execute("""
            SELECT coalesce(c.priority, d.default_priority) as eff_prio,
                   count(c.id)
            FROM cards c
            JOIN decks d ON c.deck_id = d.id
            JOIN notes n ON c.note_id = n.id
            WHERE n.user_id = ?
            GROUP BY eff_prio
            ORDER BY eff_prio DESC
        """, (user.id.hex,))
        for prio, cnt in c.fetchall():
            print(f"  Priority {prio:3d}: {cnt:3d} cards")

        # Tree structure check
        print("\n=== ROOT CHILDREN IN KNOWLEDGE TREE ORDER ===")
        ROOT_ID = "0556a75569624bbd971d71f858bbaab9"
        c.execute("""
            SELECT position, name, default_priority,
                   (SELECT count(*) FROM cards WHERE deck_id = decks.id),
                   (SELECT count(*) FROM decks d2 WHERE d2.parent_id = decks.id)
            FROM decks
            WHERE parent_id = ?
            ORDER BY position ASC, name ASC
        """, (ROOT_ID,))
        for pos, name, prio, direct_cards, subdecks in c.fetchall():
            print(f"  Pos {pos}: [{prio} prio] {name} ({direct_cards} direct cards, {subdecks} subdecks)")

        conn.close()

if __name__ == "__main__":
    asyncio.run(run_verification())
