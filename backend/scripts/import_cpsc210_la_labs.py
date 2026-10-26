"""Import CPSC 210 LA and Lab JSON decks into Ars Memoriae under parent deck CPSC 210."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import func, select
from app.db import SessionLocal
from app.models import Card, CardReference, Deck, Import, Note, NoteType, User
from app.services.note_service import default_note_type, sync_cards

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("import_cpsc210")

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
]

LAB_FILES = [
    ("6 - Labs/cpsc210_lab01_reading_the_tides.json", "Lab01 - Reading the Tides", 55, 1),
    ("6 - Labs/cpsc210_lab02_charting_the_tides.json", "Lab02 - Charting the Tides", 60, 2),
    ("6 - Labs/cpsc210_lab03_serving_the_tides.json", "Lab03 - Serving the Tides", 70, 3),
    ("6 - Labs/cpsc210_lab04_keeping_the_tides.json", "Lab04 - Keeping the Tides", 90, 4),
]


def wrap_lab_files():
    """Wrap each lab array as { "deck": ..., "priority": ..., "notes": [...] } next to original."""
    for rel_path, child_deck_name, priority, _ in LAB_FILES:
        orig_path = SOURCE_ROOT / rel_path
        with open(orig_path, "r", encoding="utf-8") as f:
            cards = json.load(f)
        
        wrapped_data = {
            "deck": child_deck_name,
            "priority": priority,
            "notes": cards,
        }
        
        wrapped_filename = orig_path.stem + "_wrapped.json"
        wrapped_path = orig_path.parent / wrapped_filename
        with open(wrapped_path, "w", encoding="utf-8") as f:
            json.dump(wrapped_data, f, indent=2, ensure_ascii=False)
        log.info(f"Wrote wrapped copy: {wrapped_path}")


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
        log.info(f"= Reusing deck: '{name}' (id={deck.id}, parent={parent_id})")
    return deck


async def run_import():
    # 1. Wrap lab files first
    log.info("Wrapping lab arrays into normalized copies...")
    wrap_lab_files()

    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == USER_EMAIL))
        if user is None:
            raise RuntimeError(f"User {USER_EMAIL} not found")
        log.info(f"Importing for user: {user.email} ({user.id})")

        # 2. Ensure Parent Deck: "CPSC 210"
        parent_deck = await ensure_deck(
            db,
            user.id,
            name="CPSC 210",
            parent_id=None,
            default_priority=80,
            position=0,
            thematic_nature="CPSC 210: Software Construction in TypeScript (Contracts, Abstraction, Testing, and Persistence)",
        )

        # 3. Ensure Sub-parent Decks: "Lecture Activities" and "Labs"
        la_parent = await ensure_deck(
            db,
            user.id,
            name="Lecture Activities",
            parent_id=parent_deck.id,
            default_priority=50,
            position=1,
            thematic_nature="PrairieLearn Lecture Activities (LA01–LA07): interactive coding exercises and contracts.",
        )

        labs_parent = await ensure_deck(
            db,
            user.id,
            name="Labs",
            parent_id=parent_deck.id,
            default_priority=70,
            position=2,
            thematic_nature="Laboratory assignments (Lab01–Lab04): Tides series.",
        )

        import_report = []
        total_notes_created = 0
        total_cards_created = 0
        total_citations_created = 0

        # Ingest LA Decks
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
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cards_list = data["notes"]
            
            created, skipped = await ingest_cards_to_deck(
                db, user, child_deck, cards_list, default_prio=prio
            )
            total_notes_created += created
            total_cards_created += created
            import_report.append({
                "group": "Lecture Activities",
                "deck": child_name,
                "file": rel_path,
                "expected": len(cards_list),
                "imported": created,
                "skipped": skipped,
            })

        # Ingest Lab Decks (using the wrapped copies)
        for rel_path, child_name, prio, pos in LAB_FILES:
            child_deck = await ensure_deck(
                db,
                user.id,
                name=child_name,
                parent_id=labs_parent.id,
                default_priority=prio,
                position=pos,
            )
            orig_path = SOURCE_ROOT / rel_path
            wrapped_path = orig_path.parent / (orig_path.stem + "_wrapped.json")
            with open(wrapped_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cards_list = data["notes"]
            
            created, skipped = await ingest_cards_to_deck(
                db, user, child_deck, cards_list, default_prio=prio
            )
            total_notes_created += created
            total_cards_created += created
            import_report.append({
                "group": "Labs",
                "deck": child_name,
                "file": rel_path,
                "expected": len(cards_list),
                "imported": created,
                "skipped": skipped,
            })

        # Record import in imports table
        db.add(
            Import(
                user_id=user.id,
                filename="cpsc210_la_and_labs",
                notes_mapped=total_notes_created,
                cards_mapped=total_cards_created,
                warnings=[],
            )
        )
        await db.commit()
        log.info("\nTransaction committed successfully.")
        return import_report


async def ingest_cards_to_deck(db, user, deck: Deck, cards_list: list[dict], default_prio: int) -> tuple[int, int]:
    # Query existing fronts and titles in this deck to prevent double-import
    existing_fronts_query = await db.execute(
        select(Note.field_values).join(Card, Card.note_id == Note.id).where(Card.deck_id == deck.id)
    )
    existing_fronts = set()
    existing_titles = set()
    for (fv,) in existing_fronts_query.all():
        if fv:
            f = str(fv.get("Front", "") or fv.get("front", "")).strip()
            if f:
                existing_fronts.add(f)
            t = str(fv.get("title", "")).strip()
            if t:
                existing_titles.add(t)

    created = 0
    skipped = 0

    for item in cards_list:
        front = (item.get("front") or item.get("title") or "").strip()
        back = (item.get("back") or "").strip()
        title = (item.get("title") or "").strip()

        if not front or not back:
            skipped += 1
            continue

        if front in existing_fronts or (title and title in existing_titles):
            skipped += 1
            continue

        existing_fronts.add(front)
        if title:
            existing_titles.add(title)

        is_code = (
            item.get("card_type") == "code"
            or bool(item.get("starter_code"))
            or bool(item.get("test_cases"))
        )

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

        profile = "math_code" if is_code else "short_answer"
        nt = await default_note_type(db, user, "basic", grading_profile=profile)
        note = Note(user_id=user.id, note_type_id=nt.id, field_values=field_values)
        db.add(note)
        await db.flush()

        tags = list(item.get("tags") or [])
        if is_code:
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

    log.info(f"  Deck '{deck.name}': {created} created, {skipped} skipped")
    return created, skipped


if __name__ == "__main__":
    import json
    report = asyncio.run(run_import())
    print("\n=== IMPORT REPORT ===")
    print(json.dumps(report, indent=2))
