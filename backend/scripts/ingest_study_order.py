"""Ingest all CPSC 210 flashcards, study guides, and configure exact study order priorities."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from sqlalchemy import select, update

from app.db import SessionLocal
from app.models import (
    Card,
    CardReference,
    Deck,
    KnowledgeNode,
    Note,
    Source,
    User,
)
from app.services.note_service import default_note_type
from app.services.tree_service import ensure_tree

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("ingest_study_order")

USER_EMAIL = "michael.r.polley@outlook.com"
CPSC_ROOT = Path(r"C:\Users\micha\OneDrive\Documents\UBC BCS ICS\CPSC 210")
FLASHCARDS_ROOT = CPSC_ROOT / "06 Flashcards"
STUDY_GUIDES_ROOT = CPSC_ROOT / "Study Guides"
MASTER_BACKUP_PATH = FLASHCARDS_ROOT / "cpsc210_all_481_cards_master_backup.json"


def norm(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def parse_datetime(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(val, fmt)
        except Exception:
            continue
    return None


async def ensure_deck(
    db,
    user_id: uuid.UUID,
    name: str,
    parent_id: uuid.UUID | None,
    default_priority: int = 50,
    position: int = 0,
    thematic_nature: str | None = None,
    documentation: str | None = None,
    source_documents: list | None = None,
    target_event_date: datetime | None = None,
    target_event_title: str | None = None,
    deck_id: uuid.UUID | None = None,
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
        deck_kwargs = {
            "user_id": user_id,
            "name": name,
            "parent_id": parent_id,
            "default_priority": default_priority,
            "position": position,
            "thematic_nature": thematic_nature,
            "documentation": documentation,
            "source_documents": list(source_documents or []),
            "target_event_date": target_event_date,
            "target_event_title": target_event_title,
        }
        if deck_id is not None:
            deck_kwargs["id"] = deck_id
        deck = Deck(**deck_kwargs)
        db.add(deck)
        await db.flush()
        log.info(f"+ Created deck: '{name}' (prio={default_priority}, pos={position})")
    else:
        deck.default_priority = default_priority
        deck.position = position
        if thematic_nature:
            deck.thematic_nature = thematic_nature
        if documentation:
            deck.documentation = documentation
        if source_documents:
            deck.source_documents = list(source_documents)
        if target_event_date:
            deck.target_event_date = target_event_date
        if target_event_title:
            deck.target_event_title = target_event_title
        await db.flush()
    return deck


async def ensure_source(
    db,
    user_id: uuid.UUID,
    title: str,
    raw_text: str | None,
    url: str | None,
    priority: int,
) -> Source:
    query = select(Source).where(
        Source.user_id == user_id,
        Source.title == title,
    )
    src = await db.scalar(query)
    if src is None:
        src = Source(
            user_id=user_id,
            title=title,
            raw_text=raw_text,
            url=url,
            priority=priority,
            status="active",
            for_reading=True,
        )
        db.add(src)
        await db.flush()
        log.info(f"+ Created Source: '{title}' (prio={priority}, len={len(raw_text or '')})")
    else:
        src.priority = priority
        if raw_text and not src.raw_text:
            src.raw_text = raw_text
        if url and not src.url:
            src.url = url
        await db.flush()
    return src


async def run_study_order_ingest():
    # 0. Backup DB
    db_file = BACKEND_DIR / "dev.db"
    backup_file = BACKEND_DIR / f"dev.db.bak_before_study_order_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if db_file.exists():
        shutil.copy2(db_file, backup_file)
        log.info(f"Database backed up to {backup_file.name}")

    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == USER_EMAIL))
        if user is None:
            raise RuntimeError(f"User {USER_EMAIL} not found")
        log.info(f"Target user: {user.email} ({user.id})")

        # NoteTypes cache
        nt_math_code = await default_note_type(db, user, "basic", grading_profile="math_code")
        nt_short_answer = await default_note_type(db, user, "basic", grading_profile="short_answer")

        # =========================================================================
        # 1. ROOT DECK & PRIMARY STUDY ORDER TRACKS
        # =========================================================================
        # Root Deck: CPSC 210
        cpsc210_root = await ensure_deck(
            db,
            user.id,
            name="CPSC 210 — every function has a contract",
            parent_id=None,
            default_priority=100,
            position=0,
            thematic_nature="Every function has a contract: preconditions, postconditions, and invariants.",
            documentation="Core course hierarchy for UBC CPSC 210 (Software Construction in TypeScript).",
        )

        # -------------------------------------------------------------------------
        # Study Track 1: Basics (13 cards, Priority 100, Position 1)
        # -------------------------------------------------------------------------
        basics_guide_pdf = str(STUDY_GUIDES_ROOT / "cpsc210-basics-study-guide.pdf")
        basics_deck = await ensure_deck(
            db,
            user.id,
            name="Basics - TypeScript Foundations (Ch 1, 2, 5, 6, 10)",
            parent_id=cpsc210_root.id,
            default_priority=100,
            position=1,
            thematic_nature="TypeScript fundamentals: primitives, branching, arrays, mutation, and classes.",
            documentation="Step 1 in study order: TypeScript foundations. Read alongside cpsc210-basics-study-guide.pdf.",
            source_documents=[{
                "name": "cpsc210-basics-study-guide.pdf",
                "path": basics_guide_pdf,
                "type": "study_guide",
            }],
        )

        # -------------------------------------------------------------------------
        # Study Track 2, 3, 4: Final Exam Prep Container & Decks (Priority 90, 80, 70, Position 2)
        # -------------------------------------------------------------------------
        final_parent_deck = await ensure_deck(
            db,
            user.id,
            name="Final Exam Prep",
            parent_id=cpsc210_root.id,
            default_priority=90,
            position=2,
            thematic_nature="Comprehensive CPSC 210 Final Exam synthesis tracks.",
            documentation="Primary final exam study tracks in recommended sequence: Track 1, Track 2, Track 3.",
        )

        p1_guide_pdf = str(STUDY_GUIDES_ROOT / "cpsc210-final-prep-1-study-guide.pdf")
        final_p1_deck = await ensure_deck(
            db,
            user.id,
            name="Final Prep 1 - Making Code Correct (Ch 3, 4, 7, 8, 9)",
            parent_id=final_parent_deck.id,
            default_priority=90,
            position=1,
            thematic_nature="Invariants, state maintenance, async effects, error handling, and test validation.",
            documentation="Step 2 in study order: Ch 3, 4, 7, 8, 9. Read alongside cpsc210-final-prep-1-study-guide.pdf.",
            source_documents=[{
                "name": "cpsc210-final-prep-1-study-guide.pdf",
                "path": p1_guide_pdf,
                "type": "study_guide",
            }],
        )

        p2_guide_pdf = str(STUDY_GUIDES_ROOT / "cpsc210-final-prep-2-study-guide.pdf")
        final_p2_deck = await ensure_deck(
            db,
            user.id,
            name="Final Prep 2 - Building Abstractions (Ch 11-16)",
            parent_id=final_parent_deck.id,
            default_priority=80,
            position=2,
            thematic_nature="Decomposition, encapsulation, subtyping/LSP, boundaries, and extension.",
            documentation="Step 3 in study order: Ch 11–16. Read alongside cpsc210-final-prep-2-study-guide.pdf.",
            source_documents=[{
                "name": "cpsc210-final-prep-2-study-guide.pdf",
                "path": p2_guide_pdf,
                "type": "study_guide",
            }],
        )

        p3_guide_pdf = str(STUDY_GUIDES_ROOT / "cpsc210-final-prep-3-study-guide.pdf")
        final_p3_deck = await ensure_deck(
            db,
            user.id,
            name="Final Prep 3 - Growing Systems (Ch 17-22)",
            parent_id=final_parent_deck.id,
            default_priority=70,
            position=3,
            thematic_nature="Coupling, data consumption/JSON, API design, refactoring, and debugging.",
            documentation="Step 4 in study order: Ch 17–22. Lectured until Dec 2. Read alongside cpsc210-final-prep-3-study-guide.pdf.",
            target_event_date=datetime(2026, 12, 2, 0, 0, 0),
            target_event_title="Ch 17-22 Lectures Complete",
            source_documents=[{
                "name": "cpsc210-final-prep-3-study-guide.pdf",
                "path": p3_guide_pdf,
                "type": "study_guide",
            }],
        )

        # -------------------------------------------------------------------------
        # Study Track 5: Older Decks - Foundations (Textbook Ch 1-7, Position 3)
        # Priority: Ch 1, 2, 5 = 65; Ch 3, 4, 6, 7, 8, 9 = 55
        # -------------------------------------------------------------------------
        foundations_deck = await ensure_deck(
            db,
            user.id,
            name="Part 1: Foundations — keep the contract",
            parent_id=cpsc210_root.id,
            default_priority=65,
            position=3,
            thematic_nature="Textbook Chapters 1-9. Fundamental concepts.",
        )

        # -------------------------------------------------------------------------
        # Study Track 6: Lecture Activities (Position 4, Priority 45)
        # -------------------------------------------------------------------------
        la_parent_deck = await ensure_deck(
            db,
            user.id,
            name="Lecture Activities",
            parent_id=cpsc210_root.id,
            default_priority=45,
            position=4,
            thematic_nature="PrairieLearn Lecture Activities (LA01–LA12).",
        )

        # -------------------------------------------------------------------------
        # Study Track 7: Midterm 3 (Position 5, Priority 35)
        # -------------------------------------------------------------------------
        mt3_parent_deck = await ensure_deck(
            db,
            user.id,
            name="Midterm 3",
            parent_id=cpsc210_root.id,
            default_priority=35,
            position=5,
            thematic_nature="Scope for Midterm 3 (Ch 8-16, practice midterm).",
        )

        # -------------------------------------------------------------------------
        # Study Track 8: Labs & Piazza (Position 6 & 7, Priority 15 - per "skip until first 4 done")
        # -------------------------------------------------------------------------
        labs_parent_deck = await ensure_deck(
            db,
            user.id,
            name="Labs",
            parent_id=cpsc210_root.id,
            default_priority=15,
            position=6,
            thematic_nature="Laboratory assignments (Lab01–Lab05).",
        )

        # Container decks for Part 2 & Part 3 curriculum
        part2_deck = await ensure_deck(
            db,
            user.id,
            name="! Part 2: Abstraction — hide behind the contract",
            parent_id=cpsc210_root.id,
            default_priority=35,
            position=7,
        )
        part3_deck = await ensure_deck(
            db,
            user.id,
            name="! Part 3: Evolution — keep contracts stable",
            parent_id=cpsc210_root.id,
            default_priority=35,
            position=8,
        )

        # =========================================================================
        # 2. UPLOAD STUDY GUIDES TO INCREMENTAL READING SOURCES
        # =========================================================================
        study_guide_sources = [
            ("CPSC 210 — Basics Study Guide", "cpsc210-basics-study-guide.tex", basics_guide_pdf, 100),
            ("CPSC 210 — Final Prep 1 Study Guide (Making Code Correct)", "cpsc210-final-prep-1-study-guide.tex", p1_guide_pdf, 90),
            ("CPSC 210 — Final Prep 2 Study Guide (Building Abstractions)", "cpsc210-final-prep-2-study-guide.tex", p2_guide_pdf, 80),
            ("CPSC 210 — Final Prep 3 Study Guide (Growing Systems)", "cpsc210-final-prep-3-study-guide.tex", p3_guide_pdf, 70),
        ]
        for title, tex_file, pdf_path, prio in study_guide_sources:
            tex_path = STUDY_GUIDES_ROOT / tex_file
            raw_text = None
            if tex_path.exists():
                with open(tex_path, encoding="utf-8", errors="ignore") as f:
                    raw_text = f.read()
            await ensure_source(db, user.id, title, raw_text, pdf_path, prio)

        # =========================================================================
        # 3. BUILD ALL MASTER BACKUP SUBDECKS WITH HIERARCHICAL PRIORITIES
        # =========================================================================
        with open(MASTER_BACKUP_PATH, encoding="utf-8") as f:
            master_data = json.load(f)

        master_decks_data = master_data.get("decks", [])
        master_cards_data = master_data.get("cards", [])

        # Map key master decks to our established hierarchy
        deck_id_map: dict[str, uuid.UUID] = {}
        deck_id_map["118f08b61e5e4ad6927ad64c0e5c8c19"] = cpsc210_root.id
        deck_id_map["51e040a5a0f146f8841da50ee63c9b46"] = foundations_deck.id
        deck_id_map["ca8a245579f143c7b39a7b973fc78278"] = la_parent_deck.id
        deck_id_map["7549efe5b774431a89ea873db8e05f6a"] = labs_parent_deck.id
        deck_id_map["df6a2dc479b14842b10a2663ce0983cb"] = mt3_parent_deck.id
        deck_id_map["8c492dc6630f4cf3a1e941199ce5b804"] = part2_deck.id
        deck_id_map["1b994e859b8a4f89839ae2f28148cb09"] = part3_deck.id

        # Determine priority for master subdecks based on user's study order
        def get_subdeck_priority(name: str, parent_pid: str | None) -> int:
            if "Ch 01" in name or "Ch 02" in name or "Ch 05" in name:
                return 65
            if parent_pid == "51e040a5a0f146f8841da50ee63c9b46":  # Foundations
                return 55
            if parent_pid == "ca8a245579f143c7b39a7b973fc78278" or "LA0" in name or "LA1" in name:  # LA
                return 45
            if parent_pid == "df6a2dc479b14842b10a2663ce0983cb" or "Midterm 3" in name or "Code ·" in name or "Carry-forward" in name:  # MT3
                return 35
            if parent_pid == "7549efe5b774431a89ea873db8e05f6a" or "Lab" in name:  # Labs
                return 15
            if "Piazza" in name:
                return 15
            return 35

        # Create master subdecks
        unprocessed = [d for d in master_decks_data if d["id"] not in deck_id_map]
        while unprocessed:
            progress = False
            remaining = []
            for d in unprocessed:
                pid = d.get("parent_id")
                if pid in deck_id_map:
                    mapped_parent_id = deck_id_map[pid]
                    target_uuid = uuid.UUID(hex=d["id"])
                    prio = get_subdeck_priority(d["name"], pid)

                    # Check existing deck
                    existing_d = await db.get(Deck, target_uuid)
                    if existing_d is None:
                        new_deck = Deck(
                            id=target_uuid,
                            user_id=user.id,
                            name=d["name"],
                            parent_id=mapped_parent_id,
                            default_priority=prio,
                            documentation=d.get("documentation"),
                            thematic_nature=d.get("thematic_nature"),
                            source_documents=list(d.get("source_documents") or []),
                        )
                        db.add(new_deck)
                        await db.flush()
                        deck_id_map[d["id"]] = new_deck.id
                    else:
                        existing_d.parent_id = mapped_parent_id
                        existing_d.default_priority = prio
                        await db.flush()
                        deck_id_map[d["id"]] = existing_d.id
                    progress = True
                else:
                    remaining.append(d)
            if not progress:
                for d in remaining:
                    target_uuid = uuid.UUID(hex=d["id"])
                    prio = get_subdeck_priority(d["name"], None)
                    existing_d = await db.get(Deck, target_uuid)
                    if existing_d is None:
                        new_deck = Deck(
                            id=target_uuid,
                            user_id=user.id,
                            name=d["name"],
                            parent_id=cpsc210_root.id,
                            default_priority=prio,
                            documentation=d.get("documentation"),
                            thematic_nature=d.get("thematic_nature"),
                            source_documents=list(d.get("source_documents") or []),
                        )
                        db.add(new_deck)
                        await db.flush()
                        deck_id_map[d["id"]] = new_deck.id
                    else:
                        deck_id_map[d["id"]] = existing_d.id
                break
            unprocessed = remaining

        # Ensure LA08 to LA12 exist under Lecture Activities
        la_decks_map = {}
        for i in range(1, 13):
            la_name = f"LA{i:02d}"
            la_d = await ensure_deck(
                db,
                user.id,
                name=la_name,
                parent_id=la_parent_deck.id,
                default_priority=45,
                position=i,
            )
            la_decks_map[la_name] = la_d

        # Ensure Lab01 to Lab05 exist under Labs
        lab_decks_map = {}
        labs_spec = [
            ("Lab01 - Reading the Tides", 1),
            ("Lab02 - Charting the Tides", 2),
            ("Lab03 - Serving the Tides", 3),
            ("Lab04 - Keeping the Tides", 4),
            ("Lab05 - Watching the Tides", 5),
        ]
        for lname, pos in labs_spec:
            lab_d = await ensure_deck(
                db,
                user.id,
                name=lname,
                parent_id=labs_parent_deck.id,
                default_priority=15,
                position=pos,
            )
            lab_decks_map[lname] = lab_d

        # Ensure MT3 subdecks exist
        await ensure_deck(
            db,
            user.id,
            name="CPSC 210 MT3 Essentials",
            parent_id=mt3_parent_deck.id,
            default_priority=35,
            position=1,
        )
        mt3_practice_deck = await ensure_deck(
            db,
            user.id,
            name="MT3 - Practice Midterm (Music Organization)",
            parent_id=mt3_parent_deck.id,
            default_priority=35,
            position=2,
        )

        # Ch 08 & Ch 09 decks under Foundations (or MT3)
        ch08_deck = await ensure_deck(
            db,
            user.id,
            name="Ch 08: Designing for Failure",
            parent_id=foundations_deck.id,
            default_priority=55,
            position=8,
            thematic_nature="Result<T, E> vs Exceptions, Recoverable Error Contracts.",
        )
        ch09_deck = await ensure_deck(
            db,
            user.id,
            name="Ch 09: Validating Behaviour",
            parent_id=foundations_deck.id,
            default_priority=55,
            position=9,
            thematic_nature="Test Suite Strength, Reference Test Suites, Fault Injection & Property Testing.",
        )

        all_decks = (await db.scalars(select(Deck).where(Deck.user_id == user.id))).all()
        decks_by_id = {d.id: d for d in all_decks}

        # Cache existing cards & notes
        existing_notes = (await db.scalars(select(Note).where(Note.user_id == user.id))).all()
        existing_fronts: set[str] = set()
        existing_norms: set[str] = set()
        existing_titles: set[str] = set()

        for note in existing_notes:
            fv = note.field_values or {}
            f = str(fv.get("Front") or fv.get("front") or fv.get("title") or "").strip()
            t = str(fv.get("title") or "").strip()
            if f:
                existing_fronts.add(f)
                existing_norms.add(norm(f))
            if t:
                existing_titles.add(t)

        log.info(f"Existing notes: {len(existing_notes)}, indexed front keys: {len(existing_fronts)}")

        # Helper to ingest card list
        async def ingest_card_list(
            card_items: list[dict],
            target_deck: Deck,
            assigned_priority: int,
            source_file_label: str = "",
            is_master: bool = False,
            allow_duplicate_title: bool = False,
        ) -> tuple[int, int]:
            added = 0
            skipped = 0
            for item in card_items:
                fv = item.get("field_values") if is_master else item
                if isinstance(fv, str):
                    try:
                        fv = json.loads(fv)
                    except Exception:
                        fv = {}
                fv = dict(fv or {})

                front = str(fv.get("Front") or fv.get("front") or fv.get("title") or item.get("front") or item.get("title") or "").strip()
                title = str(fv.get("title") or item.get("title") or "").strip()
                back = str(fv.get("Back") or fv.get("back") or item.get("back") or "").strip()

                if not front:
                    skipped += 1
                    continue

                # Check duplication: in dedicated target decks (Basics, Final Prep), allow cards specific to that deck
                if not allow_duplicate_title:
                    if front in existing_fronts or norm(front) in existing_norms or (title and title in existing_titles):
                        skipped += 1
                        continue
                else:
                    # In dedicated decks, only skip if the card is already in this deck
                    existing_in_deck = await db.scalar(
                        select(Card.id)
                        .join(Note, Card.note_id == Note.id)
                        .where(Card.deck_id == target_deck.id, Card.tags.contains([item.get("title", "")]) if item.get("title") else False)
                    )
                    if existing_in_deck:
                        skipped += 1
                        continue

                existing_fronts.add(front)
                existing_norms.add(norm(front))
                if title:
                    existing_titles.add(title)

                is_code = (
                    item.get("card_type") == "code"
                    or fv.get("card_type") == "code"
                    or bool(fv.get("starter_code"))
                    or bool(fv.get("test_cases"))
                    or bool(item.get("starter_code"))
                    or bool(item.get("test_cases"))
                )

                clean_fv = dict(fv)
                clean_fv["Front"] = front
                clean_fv["Back"] = back
                for k in [
                    "starter_code", "test_cases", "starter_tests", "time_complexity",
                    "space_complexity", "edge_cases", "title", "difficulty", "category", "language"
                ]:
                    if item.get(k) is not None and k not in clean_fv:
                        clean_fv[k] = item[k]

                nt = nt_math_code if is_code else nt_short_answer
                note = Note(user_id=user.id, note_type_id=nt.id, field_values=clean_fv)
                db.add(note)
                await db.flush()

                tags = list(item.get("tags") or fv.get("tags") or [])
                if is_code and "code" not in tags:
                    tags.append("code")

                quote = str(item.get("quote") or fv.get("quote") or "").strip()
                locator = str(item.get("locator") or fv.get("locator") or "").strip()

                card = Card(
                    note_id=note.id,
                    deck_id=target_deck.id,
                    template_slot="0",
                    priority=assigned_priority,
                    origin="imported",
                    tags=tags,
                    state="new",
                    documentation=item.get("card_documentation") or target_deck.documentation,
                    thematic_nature=target_deck.thematic_nature,
                    source_documents=list(target_deck.source_documents or []),
                )
                db.add(card)
                await db.flush()
                added += 1

                # Citations
                refs = item.get("references") or []
                if refs:
                    for r in refs:
                        q = str(r.get("quote") or "").strip()
                        loc = str(r.get("locator") or "").strip()
                        if q or loc:
                            db.add(
                                CardReference(
                                    card_id=card.id,
                                    quote=q or (f"Excerpt from {loc}" if loc else ""),
                                    quote_verified=bool(r.get("quote_verified", True)),
                                    locator=loc or None,
                                    source_title=r.get("source_title") or f"CPSC 210 — {target_deck.name}",
                                )
                            )
                elif quote or locator:
                    db.add(
                        CardReference(
                            card_id=card.id,
                            quote=quote or (f"Excerpt from {locator}" if locator else ""),
                            quote_verified=True,
                            locator=locator or None,
                            source_title=f"CPSC 210 — {target_deck.name}",
                        )
                    )

            return added, skipped

        # =========================================================================
        # 4. INGEST TOP 4 TARGET DECKS (IN EXACT STUDY ORDER)
        # =========================================================================
        log.info("Ingesting Track 1: Basics (13 cards, priority 100)...")
        basics_file = FLASHCARDS_ROOT / "7 - Basics" / "cpsc210_basics_foundations.json"
        with open(basics_file, encoding="utf-8") as f:
            basics_cards = json.load(f)
        b_add, b_skip = await ingest_card_list(
            basics_cards, basics_deck, assigned_priority=100, source_file_label="cpsc210_basics_foundations.json", allow_duplicate_title=True
        )
        log.info(f"Basics: {b_add} added, {b_skip} skipped.")

        log.info("Ingesting Track 2: Final Prep 1 (11 cards, priority 90)...")
        fp1_file = FLASHCARDS_ROOT / "8 - Final" / "cpsc210_final_p1_making_code_correct.json"
        with open(fp1_file, encoding="utf-8") as f:
            fp1_cards = json.load(f)
        fp1_add, fp1_skip = await ingest_card_list(
            fp1_cards, final_p1_deck, assigned_priority=90, source_file_label="cpsc210_final_p1_making_code_correct.json", allow_duplicate_title=True
        )
        log.info(f"Final Prep 1: {fp1_add} added, {fp1_skip} skipped.")

        log.info("Ingesting Track 3: Final Prep 2 (11 cards, priority 80)...")
        fp2_file = FLASHCARDS_ROOT / "8 - Final" / "cpsc210_final_p2_building_abstractions.json"
        with open(fp2_file, encoding="utf-8") as f:
            fp2_cards = json.load(f)
        fp2_add, fp2_skip = await ingest_card_list(
            fp2_cards, final_p2_deck, assigned_priority=80, source_file_label="cpsc210_final_p2_building_abstractions.json", allow_duplicate_title=True
        )
        log.info(f"Final Prep 2: {fp2_add} added, {fp2_skip} skipped.")

        log.info("Ingesting Track 4: Final Prep 3 (11 cards, priority 70)...")
        fp3_file = FLASHCARDS_ROOT / "8 - Final" / "cpsc210_final_p3_growing_systems.json"
        with open(fp3_file, encoding="utf-8") as f:
            fp3_cards = json.load(f)
        fp3_add, fp3_skip = await ingest_card_list(
            fp3_cards, final_p3_deck, assigned_priority=70, source_file_label="cpsc210_final_p3_growing_systems.json", allow_duplicate_title=True
        )
        log.info(f"Final Prep 3: {fp3_add} added, {fp3_skip} skipped.")

        # =========================================================================
        # 5. INGEST MASTER BACKUP CARDS
        # =========================================================================
        log.info("Ingesting master backup cards...")
        m_add = 0
        m_skip = 0
        for c_data in master_cards_data:
            raw_deck_id = c_data.get("deck_id")
            target_uuid = deck_id_map.get(raw_deck_id)
            target_deck = decks_by_id.get(target_uuid) if target_uuid else foundations_deck
            prio = target_deck.default_priority if target_deck else 50
            a, s = await ingest_card_list([c_data], target_deck, assigned_priority=prio, is_master=True)
            m_add += a
            m_skip += s
        log.info(f"Master backup: {m_add} added, {m_skip} skipped.")

        # =========================================================================
        # 6. INGEST REMAINING CHAPTER 8 & 9 TEXTBOOK CARDS & REWRITES
        # =========================================================================
        tb_dir = FLASHCARDS_ROOT / "3 - Textbook Ch1-7"
        if tb_dir.exists():
            for fname in os.listdir(tb_dir):
                if not fname.endswith(".json") or fname.endswith("_wrapped.json"):
                    continue
                fpath = tb_dir / fname
                with open(fpath, encoding="utf-8") as f:
                    data = json.load(f)
                notes = data if isinstance(data, list) else data.get("notes", [])
                t_deck = ch08_deck if "ch8" in fname else (ch09_deck if "ch9" in fname else foundations_deck)
                prio = 55
                await ingest_card_list(notes, t_deck, assigned_priority=prio, source_file_label=fname)

        # Ingest LA08-LA12
        la_dir = FLASHCARDS_ROOT / "1 - LA decks"
        if la_dir.exists():
            for i in range(8, 13):
                laf = la_dir / f"cpsc210_mt3_LA{i:02d}.json"
                if laf.exists():
                    with open(laf, encoding="utf-8") as f:
                        data = json.load(f)
                    notes = data if isinstance(data, list) else data.get("notes", [])
                    t_deck = la_decks_map.get(f"LA{i:02d}", la_parent_deck)
                    await ingest_card_list(notes, t_deck, assigned_priority=45, source_file_label=laf.name)

        # Ingest Lab 5
        lab5_file = FLASHCARDS_ROOT / "6 - Labs" / "cpsc210_lab05_watching_the_tides.json"
        if lab5_file.exists():
            with open(lab5_file, encoding="utf-8") as f:
                data = json.load(f)
            notes = data if isinstance(data, list) else data.get("notes", [])
            t_deck = lab_decks_map.get("Lab05 - Watching the Tides", labs_parent_deck)
            await ingest_card_list(notes, t_deck, assigned_priority=15, source_file_label=lab5_file.name)

        # Ingest MT3 practice midterm
        mt3_prac_file = FLASHCARDS_ROOT / "5 - MT3" / "cpsc210_mt3_practice_midterm.json"
        if mt3_prac_file.exists():
            with open(mt3_prac_file, encoding="utf-8") as f:
                data = json.load(f)
            notes = data if isinstance(data, list) else data.get("notes", [])
            await ingest_card_list(notes, mt3_practice_deck, assigned_priority=35, source_file_label=mt3_prac_file.name)

        # Commit all card data
        await db.commit()
        log.info("All cards and sources committed successfully.")

        # =========================================================================
        # 7. SYNC KNOWLEDGE NODES TREE
        # =========================================================================
        log.info("Syncing Knowledge Nodes tree...")
        await ensure_tree(db, user)
        await db.commit()
        log.info("Knowledge tree synchronized successfully.")

        # Also sync KnowledgeNode positions with Deck positions
        decks_rows = (await db.execute(select(Deck.id, Deck.position).where(Deck.user_id == user.id))).all()
        for did, pos in decks_rows:
            await db.execute(
                update(KnowledgeNode)
                .where(KnowledgeNode.deck_id == did)
                .values(position=pos)
            )
        await db.commit()
        log.info("Knowledge node positions synchronized.")


if __name__ == "__main__":
    asyncio.run(run_study_order_ingest())
    print("\n=== INGEST & STUDY ORDER COMPLETE ===")
