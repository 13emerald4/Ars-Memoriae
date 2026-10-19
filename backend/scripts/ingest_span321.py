"""Ingest SPAN 321 Exam 1 subdecks into Ars Memoriae.

Extracts SPAN321_Exam1_Subdecks.zip to course folders and populates:
- Parent deck: SPAN321_Exam1_Core_AllPriorities (0 direct cards, 47 total with subdecks)
- Subdeck 1: SPAN321_Exam1_P1_Highest (20 cards, priority 90)
- Subdeck 2: SPAN321_Exam1_P2_Likely (16 cards, priority 70)
- Subdeck 3: SPAN321_Exam1_P3_Supporting (11 cards, priority 40)
"""

from __future__ import annotations

import asyncio
import json
import logging
import zipfile
from datetime import datetime
from pathlib import Path
import sys

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select, func
from app.db import SessionLocal
from app.models import Card, CardReference, Deck, Import, Note, NoteType, User
from app.services.note_service import default_note_type, sync_cards

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("ingest_span321")

USER_EMAIL = "michael.r.polley@outlook.com"
ZIP_PATH = Path(r"C:\Users\micha\OneDrive\Documents\UBC BCS ICS\SPAN 321\SPAN321_Exam1_Subdecks.zip")
ONEDRIVE_COURSE_DIR = Path(r"C:\Users\micha\OneDrive\Documents\UBC BCS ICS\SPAN 321")

EXAM_DATE = datetime(2026, 10, 21, 12, 30, 0)
EXAM_TITLE = "Primer Examen"

SUBDECK_SPECS = [
    {
        "filename": "SPAN321_Exam1_P1_Highest.json",
        "name": "SPAN321_Exam1_P1_Highest",
        "priority": 90,
        "position": 1,
        "thematic_nature": "P1 — Máximo rendimiento: preguntas modelo de examen, esquemas de ensayo y conceptos clave.",
        "documentation": "20 tarjetas de máxima prioridad (P1) para el Primer Examen (21 de octubre).",
    },
    {
        "filename": "SPAN321_Exam1_P2_Likely.json",
        "name": "SPAN321_Exam1_P2_Likely",
        "priority": 70,
        "position": 2,
        "thematic_nature": "P2 — Conceptos de apoyo y desarrollo temático (Tartesos, Roma, cristianismo, arte y datos de Marisol).",
        "documentation": "16 tarjetas de probabilidad alta/media (P2) para el Primer Examen (21 de octubre).",
    },
    {
        "filename": "SPAN321_Exam1_P3_Supporting.json",
        "name": "SPAN321_Exam1_P3_Supporting",
        "priority": 40,
        "position": 3,
        "thematic_nature": "P3 — Contexto de fondo, geografía e introducción territorial peninsular.",
        "documentation": "11 tarjetas de soporte y contextualización (P3) para el Primer Examen (21 de octubre).",
    },
]


def extract_zip_files():
    """Unpack JSON files to local OneDrive directories."""
    log.info(f"Extracting zip: {ZIP_PATH}")
    if not ZIP_PATH.exists():
        raise FileNotFoundError(f"Zip file not found: {ZIP_PATH}")

    target_dirs = [
        ONEDRIVE_COURSE_DIR / "06 Flashcards",
        ONEDRIVE_COURSE_DIR / "SPAN321_Exam1_Subdecks",
    ]

    with zipfile.ZipFile(ZIP_PATH) as z:
        for tdir in target_dirs:
            tdir.mkdir(parents=True, exist_ok=True)
            z.extractall(tdir)
            log.info(f"  -> Extracted files to: {tdir}")


async def ingest():
    extract_zip_files()

    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == USER_EMAIL))
        if user is None:
            raise RuntimeError(f"User with email '{USER_EMAIL}' not found")
        log.info(f"Ingesting for user: {user.email} (id={user.id})")

        # 1. Ensure Parent Deck: SPAN321_Exam1_Core_AllPriorities
        parent_name = "SPAN321_Exam1_Core_AllPriorities"
        parent_deck = await db.scalar(
            select(Deck).where(Deck.user_id == user.id, Deck.name == parent_name)
        )
        if parent_deck is None:
            parent_deck = Deck(
                user_id=user.id,
                name=parent_name,
                parent_id=None,
                default_priority=80,
                position=0,
                target_event_title=EXAM_TITLE,
                target_event_date=EXAM_DATE,
                thematic_nature="SPAN 321: Primer Examen — Tradición y diversidad en la historia y cultura españolas.",
                documentation=(
                    "SPAN 321 — Guía de Repaso Socrática: Primer Examen (Miércoles 21 de octubre, 12:30–2:00). "
                    "Contiene los tres subdecks de prioridades (P1 Highest, P2 Likely, P3 Supporting)."
                ),
                source_documents=[{
                    "name": "span321_guia_repaso.tex",
                    "title": "SPAN 321 — Guía de Repaso Socrática: Primer Examen",
                }],
            )
            db.add(parent_deck)
            await db.flush()
            log.info(f"+ Created parent deck: '{parent_name}' (id={parent_deck.id})")
        else:
            parent_deck.target_event_title = EXAM_TITLE
            parent_deck.target_event_date = EXAM_DATE
            parent_deck.default_priority = 80
            parent_deck.position = 0
            log.info(f"Parent deck exists: '{parent_name}' (id={parent_deck.id})")

        # Get default basic note type
        basic_nt = await default_note_type(db, user, "basic", grading_profile="short_answer")

        with zipfile.ZipFile(ZIP_PATH) as z:
            total_notes_created = 0
            total_cards_created = 0
            total_citations_created = 0

            for spec in SUBDECK_SPECS:
                sub_name = spec["name"]
                sub_deck = await db.scalar(
                    select(Deck).where(Deck.user_id == user.id, Deck.name == sub_name)
                )
                if sub_deck is None:
                    sub_deck = Deck(
                        user_id=user.id,
                        name=sub_name,
                        parent_id=parent_deck.id,
                        default_priority=spec["priority"],
                        position=spec["position"],
                        target_event_title=EXAM_TITLE,
                        target_event_date=EXAM_DATE,
                        thematic_nature=spec["thematic_nature"],
                        documentation=spec["documentation"],
                        source_documents=[{
                            "name": "span321_guia_repaso.tex",
                            "title": "SPAN 321 — Guía de Repaso Socrática: Primer Examen",
                        }],
                    )
                    db.add(sub_deck)
                    await db.flush()
                    log.info(f"+ Created subdeck: '{sub_name}' (id={sub_deck.id}) under '{parent_name}'")
                else:
                    sub_deck.parent_id = parent_deck.id
                    sub_deck.default_priority = spec["priority"]
                    sub_deck.position = spec["position"]
                    sub_deck.target_event_title = EXAM_TITLE
                    sub_deck.target_event_date = EXAM_DATE
                    sub_deck.thematic_nature = spec["thematic_nature"]
                    sub_deck.documentation = spec["documentation"]
                    log.info(f"Subdeck exists: '{sub_name}' (id={sub_deck.id})")

                # Load cards for this subdeck from zip
                data = json.loads(z.read(spec["filename"]).decode("utf-8"))
                log.info(f"Processing {len(data)} items from {spec['filename']} into subdeck '{sub_name}'")

                # Existing fronts in this subdeck to avoid duplicate creation
                existing_fronts_query = await db.execute(
                    select(Note.field_values).join(Card, Card.note_id == Note.id).where(Card.deck_id == sub_deck.id)
                )
                existing_fronts = {
                    str((fv or {}).get("Front", "")).strip()
                    for (fv,) in existing_fronts_query.all()
                }

                notes_in_sub = 0
                cards_in_sub = 0

                for item in data:
                    front = (item.get("front") or "").strip()
                    back = (item.get("back") or "").strip()
                    if not front or not back:
                        continue
                    if front in existing_fronts:
                        continue
                    existing_fronts.add(front)

                    note_row = Note(
                        user_id=user.id,
                        note_type_id=basic_nt.id,
                        field_values={"Front": front, "Back": back},
                    )
                    db.add(note_row)
                    await db.flush()

                    tags = list(item.get("tags") or [])
                    for t in ["span321", "exam1", f"p{spec['position']}"]:
                        if t not in tags:
                            tags.append(t)

                    locator = (item.get("locator") or "").strip()
                    quote = (item.get("quote") or "").strip()
                    source_title = (item.get("source_title") or "SPAN 321 · Guía de Repaso Socrática: Primer Examen").strip()

                    doc_parts = []
                    if locator:
                        doc_parts.append(f"**Locator**: {locator}")
                    if quote:
                        doc_parts.append(f'**Key Quote**: "{quote}"')
                    card_doc = "\n\n".join(doc_parts) if doc_parts else sub_deck.documentation

                    cards = await sync_cards(
                        db,
                        note_row,
                        basic_nt,
                        sub_deck.id,
                        tags=tags,
                        priority=spec["priority"],
                        origin="manual",
                        documentation=card_doc,
                        thematic_nature=sub_deck.thematic_nature,
                        source_documents=[{
                            "name": "span321_guia_repaso.tex",
                            "locator": locator,
                            "quote": quote,
                            "source_file": spec["filename"],
                        }],
                    )
                    notes_in_sub += 1
                    cards_in_sub += len(cards)

                    if quote or locator:
                        for c in cards:
                            db.add(CardReference(
                                card_id=c.id,
                                quote=quote or (f"Excerpt from {locator}" if locator else ""),
                                quote_verified=True,
                                locator=locator,
                                source_title=source_title,
                            ))
                            total_citations_created += 1

                log.info(f"  -> Added {notes_in_sub} notes, {cards_in_sub} cards to '{sub_name}'")
                total_notes_created += notes_in_sub
                total_cards_created += cards_in_sub

            # Add import record
            db.add(Import(
                user_id=user.id,
                filename="json:SPAN321_Exam1_Subdecks",
                notes_mapped=total_notes_created,
                cards_mapped=total_cards_created,
                warnings=[],
            ))

            await db.commit()

        # Print summary
        log.info("\n=== INGESTION SUMMARY ===")
        log.info(f"Total notes created: {total_notes_created}")
        log.info(f"Total cards created: {total_cards_created}")
        log.info(f"Total citations created: {total_citations_created}")

        # Verify rollups
        p_count = await db.scalar(select(func.count()).select_from(Card).where(Card.deck_id == parent_deck.id))
        log.info(f"Parent deck '{parent_name}' direct cards: {p_count}")
        for spec in SUBDECK_SPECS:
            sub = await db.scalar(select(Deck).where(Deck.user_id == user.id, Deck.name == spec["name"]))
            c_count = await db.scalar(select(func.count()).select_from(Card).where(Card.deck_id == sub.id))
            log.info(f"Subdeck '{spec['name']}' direct cards: {c_count} (expected: {len(json.loads(zipfile.ZipFile(ZIP_PATH).read(spec['filename']).decode('utf-8')))})")


if __name__ == "__main__":
    asyncio.run(ingest())
