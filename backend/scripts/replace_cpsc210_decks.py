"""Replace CPSC 210 LA and Lab decks in Ars Memoriae with clean, verbatim decks."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from sqlalchemy import delete, select

from app.db import SessionLocal
from app.models import Card, CardReference, Deck, Import, Note, ReviewLog, User
from app.services.note_service import default_note_type, sync_cards

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("replace_cpsc210")

USER_EMAIL = "michael.r.polley@outlook.com"
SOURCE_ROOT = Path(r"C:\Users\micha\OneDrive\Documents\UBC BCS ICS\CPSC 210\06 Flashcards")

LA_FILES = [
    ("1 - LA decks/cpsc210_mt2_LA01.json", "LA01", 50, 1),
    ("1 - LA decks/cpsc210_mt2_LA02.json", "LA02", 50, 2),
    ("1 - LA decks/cpsc210_mt2_LA03.json", "LA03", 50, 3),
    ("1 - LA decks/cpsc210_mt2_LA04.json", "LA04", 50, 4),
    ("1 - LA decks/cpsc210_mt2_LA05.json", "LA05", 50, 5),
    ("1 - LA decks/cpsc210_mt2_LA06.json", "LA06", 50, 6),
    ("1 - LA decks/cpsc210_mt2_LA07.json", "LA07", 50, 7),
    ("1 - LA decks/cpsc210_mt3_LA08.json", "LA08", 50, 8),
    ("1 - LA decks/cpsc210_mt3_LA09.json", "LA09", 50, 9),
    ("1 - LA decks/cpsc210_mt3_LA10.json", "LA10", 50, 10),
    ("1 - LA decks/cpsc210_mt3_LA11.json", "LA11", 50, 11),
    ("1 - LA decks/cpsc210_mt3_LA12.json", "LA12", 50, 12),
]

LAB_FILES = [
    ("6 - Labs/cpsc210_lab01_reading_the_tides_wrapped.json", "Lab01 - Reading the Tides", 55, 1),
    ("6 - Labs/cpsc210_lab02_charting_the_tides_wrapped.json", "Lab02 - Charting the Tides", 60, 2),
    ("6 - Labs/cpsc210_lab03_serving_the_tides_wrapped.json", "Lab03 - Serving the Tides", 70, 3),
    ("6 - Labs/cpsc210_lab04_keeping_the_tides_wrapped.json", "Lab04 - Keeping the Tides", 90, 4),
    ("6 - Labs/cpsc210_lab05_watching_the_tides_wrapped.json", "Lab05 - Watching the Tides", 90, 5),
]


async def ensure_deck(db, user_id, name: str, parent_id, default_priority: int, position: int, thematic_nature: str | None = None) -> Deck:
    query = select(Deck).where(
        Deck.user_id == user_id,
        Deck.name == name,
    )
    if parent_id is None:
        query = query.where(Deck.parent_id.is_(None))
    else:
        query = query.where(Deck.parent_id == parent_id)

    deck = await db.scalar(query)
    if deck is None:
        deck = Deck(
            user_id=user_id,
            name=name,
            parent_id=parent_id,
            default_priority=default_priority,
            position=position,
            thematic_nature=thematic_nature,
        )
        db.add(deck)
        await db.flush()
        log.info(f"+ Created deck: '{name}' (id={deck.id}, parent={parent_id})")
    else:
        # update metadata
        deck.default_priority = default_priority
        deck.position = position
        if thematic_nature:
            deck.thematic_nature = thematic_nature
        await db.flush()
        log.info(f"= Reusing deck: '{name}' (id={deck.id}, parent={parent_id})")
    return deck


async def replace_cards_in_deck(db, user, deck: Deck, cards_list: list[dict], default_prio: int) -> int:
    """Deletes all existing cards and notes in the deck, then ingests clean cards_list."""
    # 1. Find all existing cards in this deck
    existing_cards = (await db.scalars(select(Card).where(Card.deck_id == deck.id))).all()
    card_ids = [c.id for c in existing_cards]
    note_ids = list({c.note_id for c in existing_cards})

    if card_ids:
        # Delete references
        await db.execute(delete(CardReference).where(CardReference.card_id.in_(card_ids)))
        # Delete review logs if any
        await db.execute(delete(ReviewLog).where(ReviewLog.card_id.in_(card_ids)))
        # Delete cards
        await db.execute(delete(Card).where(Card.deck_id == deck.id))
        log.info(f"  Deck '{deck.name}': purged {len(card_ids)} old cards")

    if note_ids:
        # Delete notes
        await db.execute(delete(Note).where(Note.id.in_(note_ids)))
        log.info(f"  Deck '{deck.name}': purged {len(note_ids)} old notes")

    await db.flush()

    # 2. Ingest clean cards
    created = 0
    for item in cards_list:
        front = (item.get("front") or item.get("title") or "").strip()
        back = (item.get("back") or "").strip()

        if not front or not back:
            continue

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

        profile = "math_code"
        nt = await default_note_type(db, user, "basic", grading_profile=profile)
        note = Note(user_id=user.id, note_type_id=nt.id, field_values=field_values)
        db.add(note)
        await db.flush()

        tags = list(item.get("tags") or [])
        if "code" not in tags:
            tags.append("code")
        if item.get("difficulty") and item.get("difficulty") not in tags:
            tags.append(item["difficulty"])
        if item.get("category") and item.get("category") not in tags:
            tags.append(item["category"])

        card_priority = item.get("priority") if item.get("priority") is not None else default_prio
        cards = await sync_cards(
            db, note, nt, deck.id, tags=tags, priority=card_priority, origin="manual"
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

    log.info(f"  Deck '{deck.name}': created {created} fresh cards")
    return created


async def run_replace():
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == USER_EMAIL))
        if user is None:
            raise RuntimeError(f"User {USER_EMAIL} not found")
        log.info(f"Operating for user: {user.email} ({user.id})")

        # 1. Ensure Root Deck: "CPSC 210"
        parent_deck = await ensure_deck(
            db,
            user.id,
            name="CPSC 210",
            parent_id=None,
            default_priority=80,
            position=0,
            thematic_nature="CPSC 210: Software Construction in TypeScript (Contracts, Abstraction, Testing, and Persistence)",
        )

        # 2. Ensure Sub-parent Decks: "Lecture Activities" and "Labs"
        la_parent = await ensure_deck(
            db,
            user.id,
            name="Lecture Activities",
            parent_id=parent_deck.id,
            default_priority=50,
            position=1,
            thematic_nature="PrairieLearn Lecture Activities (LA01–LA12): interactive coding exercises and contracts.",
        )

        labs_parent = await ensure_deck(
            db,
            user.id,
            name="Labs",
            parent_id=parent_deck.id,
            default_priority=70,
            position=2,
            thematic_nature="Laboratory assignments (Lab01–Lab05): Tides series.",
        )

        report = []
        total_la_cards = 0
        total_lab_cards = 0

        # Ingest LA Decks
        log.info("\n=== REPLACING LECTURE ACTIVITIES ===")
        for rel_path, child_name, prio, pos in LA_FILES:
            child_deck = await ensure_deck(
                db,
                user.id,
                name=child_name,
                parent_id=la_parent.id,
                default_priority=prio,
                position=pos,
            )
            file_path = SOURCE_ROOT / rel_path
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            cards_list = data["notes"]

            created = await replace_cards_in_deck(db, user, child_deck, cards_list, default_prio=prio)
            total_la_cards += created
            report.append({
                "group": "Lecture Activities",
                "deck": child_name,
                "file": rel_path,
                "cards": created,
            })

        # Ingest Lab Decks
        log.info("\n=== REPLACING LABS ===")
        for rel_path, child_name, prio, pos in LAB_FILES:
            child_deck = await ensure_deck(
                db,
                user.id,
                name=child_name,
                parent_id=labs_parent.id,
                default_priority=prio,
                position=pos,
            )
            file_path = SOURCE_ROOT / rel_path
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            cards_list = data["notes"]

            created = await replace_cards_in_deck(db, user, child_deck, cards_list, default_prio=prio)
            total_lab_cards += created
            report.append({
                "group": "Labs",
                "deck": child_name,
                "file": rel_path,
                "cards": created,
            })

        # Record import in imports table
        db.add(
            Import(
                user_id=user.id,
                filename="cpsc210_replacement_verbatim",
                notes_mapped=total_la_cards + total_lab_cards,
                cards_mapped=total_la_cards + total_lab_cards,
                warnings=[],
            )
        )
        await db.commit()
        log.info("\nTransaction committed successfully.")
        return report


if __name__ == "__main__":
    report = asyncio.run(run_replace())
    print("\n=== FINAL REPLACEMENT REPORT ===")
    print(json.dumps(report, indent=2))
