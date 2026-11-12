"""Ingest the CPSC 210 Practice Midterm 3 deck into Ars Memoriae."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import os
db_path = (BACKEND_DIR / "dev.db").resolve()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from sqlalchemy import delete, select
from app.db import SessionLocal
from app.models import Card, CardReference, Deck, Import, Note, NoteType, ReviewLog, User
from app.services.note_service import default_note_type, sync_cards

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("import_mt3_practice")

USER_EMAIL = "michael.r.polley@outlook.com"
PRIMARY_DECK_PATH = Path(r"C:\Users\micha\OneDrive\Documents\UBC BCS ICS\CPSC 210\Midterm 3\cpsc210_mt3_practice_midterm_wrapped.json")
BACKUP_DECK_PATH = Path(r"C:\Users\micha\OneDrive\Documents\UBC BCS ICS\CPSC 210\06 Flashcards\5 - MT3\cpsc210_mt3_practice_midterm_wrapped.json")

MT3_DATE = datetime(2026, 11, 13, 14, 0, 0, tzinfo=timezone.utc)


async def ensure_deck(
    db,
    user_id,
    name: str,
    parent_id,
    default_priority: int,
    position: int,
    thematic_nature: str | None = None,
    documentation: str | None = None,
    target_event_title: str | None = None,
    target_event_date: datetime | None = None,
) -> Deck:
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
            documentation=documentation,
            target_event_title=target_event_title,
            target_event_date=target_event_date,
        )
        db.add(deck)
        await db.flush()
        log.info(f"+ Created deck: '{name}' (id={deck.id}, parent={parent_id})")
    else:
        deck.default_priority = default_priority
        deck.position = position
        if thematic_nature:
            deck.thematic_nature = thematic_nature
        if documentation:
            deck.documentation = documentation
        if target_event_title:
            deck.target_event_title = target_event_title
        if target_event_date:
            deck.target_event_date = target_event_date
        await db.flush()
        log.info(f"= Reusing deck: '{name}' (id={deck.id}, parent={parent_id})")
    return deck


async def replace_cards_in_deck(db, user, deck: Deck, cards_list: list[dict], default_prio: int) -> int:
    """Deletes all existing cards and notes in the deck, then ingests clean cards_list."""
    existing_cards = (await db.scalars(select(Card).where(Card.deck_id == deck.id))).all()
    card_ids = [c.id for c in existing_cards]
    note_ids = list({c.note_id for c in existing_cards})

    if card_ids:
        await db.execute(delete(CardReference).where(CardReference.card_id.in_(card_ids)))
        await db.execute(delete(ReviewLog).where(ReviewLog.card_id.in_(card_ids)))
        await db.execute(delete(Card).where(Card.deck_id == deck.id))
        log.info(f"  Deck '{deck.name}': purged {len(card_ids)} old cards")

    if note_ids:
        await db.execute(delete(Note).where(Note.id.in_(note_ids)))
        log.info(f"  Deck '{deck.name}': purged {len(note_ids)} old notes")

    await db.flush()

    created = 0
    for i, item in enumerate(cards_list):
        front = (item.get("front") or item.get("title") or "").strip()
        back = (item.get("back") or "").strip()
        title = (item.get("title") or "").strip()

        # If Task 3.0 has no title, provide a descriptive one
        if not title and "Task 3.0" in front:
            title = "Practice MT3 · Task 3.0: Organizers Design"

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
            "difficulty",
            "category",
        ]:
            if item.get(k):
                field_values[k] = item[k]
        if title:
            field_values["title"] = title

        is_code = (
            item.get("card_type") == "code"
            or bool(item.get("starter_code"))
            or bool(item.get("test_cases"))
        )

        profile = "math_code" if is_code else "short_answer"
        nt = await default_note_type(db, user, "basic", grading_profile=profile)
        note = Note(user_id=user.id, note_type_id=nt.id, field_values=field_values)
        db.add(note)
        await db.flush()

        tags = list(item.get("tags") or [])
        if "cpsc210" not in tags:
            tags.append("cpsc210")
        if "mt3" not in tags:
            tags.append("mt3")
        if is_code and "code" not in tags:
            tags.append("code")
        if item.get("difficulty") and item.get("difficulty") not in tags:
            tags.append(item["difficulty"])
        if item.get("category") and item.get("category") not in tags:
            tags.append(item["category"])

        doc_parts = []
        locator = (item.get("locator") or "").strip()
        quote = (item.get("quote") or "").strip()
        if locator:
            doc_parts.append(f"**Locator**: {locator}")
        if quote:
            doc_parts.append(f'**Key Quote**: "{quote}"')
        if item.get("time_complexity") or item.get("space_complexity"):
            doc_parts.append(
                f"**Complexity**: Time `{item.get('time_complexity', 'N/A')}`, "
                f"Space `{item.get('space_complexity', 'N/A')}`"
            )
        if item.get("edge_cases"):
            doc_parts.append("**Edge Cases**: " + ", ".join(item["edge_cases"]))
        card_documentation = "\n\n".join(doc_parts) if doc_parts else deck.documentation

        card_priority = item.get("priority") if item.get("priority") is not None else default_prio
        cards = await sync_cards(
            db,
            note,
            nt,
            deck.id,
            tags=tags,
            priority=card_priority,
            origin="manual",
            documentation=card_documentation,
        )
        for card in cards:
            card.position = i + 1
        await db.flush()
        created += len(cards)

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


async def run_import():
    json_path = PRIMARY_DECK_PATH if PRIMARY_DECK_PATH.exists() else BACKUP_DECK_PATH
    if not json_path.exists():
        raise FileNotFoundError(f"Deck file not found at {PRIMARY_DECK_PATH} or {BACKUP_DECK_PATH}")

    log.info(f"Loading deck data from: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        deck_data = json.load(f)

    deck_name = deck_data.get("deck", "MT3 - Practice Midterm (Music Organization)")
    deck_priority = deck_data.get("priority", 95)
    notes_list = deck_data.get("notes", [])

    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == USER_EMAIL))
        if user is None:
            raise RuntimeError(f"User {USER_EMAIL} not found")
        log.info(f"Operating for user: {user.email} ({user.id})")

        # 1. Ensure Root Deck: "CPSC 210"
        cpsc210_deck = await ensure_deck(
            db,
            user.id,
            name="CPSC 210",
            parent_id=None,
            default_priority=80,
            position=0,
            thematic_nature="CPSC 210: Software Construction in TypeScript (Contracts, Abstraction, Testing, and Persistence)",
        )

        # 2. Ensure Midterm 3 sub-parent deck under "CPSC 210"
        mt3_parent = await ensure_deck(
            db,
            user.id,
            name="Midterm 3",
            parent_id=cpsc210_deck.id,
            default_priority=90,
            position=3,
            thematic_nature="CPSC 210 Midterm 3 Preparation: Designing for Failure, Validating Behaviour, Abstraction, Decomposition, Boundaries, Inheritance, and Practice Exams.",
            documentation="All Midterm 3 study material, including high-yield carry-forward concepts, textbook chapters 8-16, and full practice midterm exams.",
            target_event_title="Midterm 3",
            target_event_date=MT3_DATE,
        )

        # 3. Ensure the Practice Midterm subdeck under "Midterm 3"
        practice_deck = await ensure_deck(
            db,
            user.id,
            name=deck_name,
            parent_id=mt3_parent.id,
            default_priority=deck_priority,
            position=1,
            thematic_nature="Official Practice Midterm 3: Music Organization system (Playlist genre frequencies, Album testing, and generic OrderedSet organizers).",
            documentation="Practice exam covering Tasks 1.1–1.2 (Playlist functions), Task 2 (Album testing), and Tasks 3.0–3.3 (Generic OrderedSet and organizers).",
            target_event_title="Midterm 3",
            target_event_date=MT3_DATE,
        )

        # 4. Ingest cards into the practice deck
        created = await replace_cards_in_deck(db, user, practice_deck, notes_list, default_prio=deck_priority)

        # 5. Record Import
        db.add(
            Import(
                user_id=user.id,
                filename=f"json:{deck_name}",
                notes_mapped=created,
                cards_mapped=created,
                warnings=[],
            )
        )
        await db.commit()
        log.info("\nImport committed successfully!")

        return {
            "root_deck": cpsc210_deck.name,
            "parent_deck": mt3_parent.name,
            "deck": practice_deck.name,
            "deck_id": str(practice_deck.id),
            "cards_created": created,
            "priority": deck_priority,
        }


if __name__ == "__main__":
    result = asyncio.run(run_import())
    print("\n=== IMPORT RESULT ===")
    print(json.dumps(result, indent=2))
