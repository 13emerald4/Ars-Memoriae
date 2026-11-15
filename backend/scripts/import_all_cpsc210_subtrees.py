"""Import all CPSC 210 flashcards and complete hierarchical subtrees into Ars Memoriae."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
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
    Import,
    KnowledgeNode,
    Note,
    NoteType,
    User,
)
from app.services.note_service import default_note_type, sync_cards
from app.services.tree_service import ensure_tree

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("import_cpsc210_subtrees")

USER_EMAIL = "michael.r.polley@outlook.com"
SOURCE_ROOT = Path(r"C:\Users\micha\OneDrive\Documents\UBC BCS ICS\CPSC 210\06 Flashcards")
MASTER_BACKUP_PATH = SOURCE_ROOT / "cpsc210_all_481_cards_master_backup.json"


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
    thematic_nature: str | None = None,
    documentation: str | None = None,
    source_documents: list | None = None,
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
            "thematic_nature": thematic_nature,
            "documentation": documentation,
            "source_documents": list(source_documents or []),
        }
        if deck_id is not None:
            deck_kwargs["id"] = deck_id
        deck = Deck(**deck_kwargs)
        db.add(deck)
        await db.flush()
        log.info(f"+ Created deck: '{name}' (id={deck.id}, parent={parent_id})")
    else:
        # Update metadata if missing
        updated = False
        if thematic_nature and not deck.thematic_nature:
            deck.thematic_nature = thematic_nature
            updated = True
        if documentation and not deck.documentation:
            deck.documentation = documentation
            updated = True
        if source_documents and not deck.source_documents:
            deck.source_documents = list(source_documents)
            updated = True
        if updated:
            await db.flush()
    return deck


async def run_import():
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == USER_EMAIL))
        if user is None:
            raise RuntimeError(f"User {USER_EMAIL} not found")
        log.info(f"Target user: {user.email} ({user.id})")

        # 1. Cache existing decks
        existing_decks = (
            await db.scalars(select(Deck).where(Deck.user_id == user.id))
        ).all()
        decks_by_name = {d.name: d for d in existing_decks}
        decks_by_id = {d.id: d for d in existing_decks}
        log.info(f"Existing DB decks: {len(existing_decks)}")

        # 2. Cache existing card fronts to prevent any duplication
        existing_notes = (
            await db.scalars(select(Note).where(Note.user_id == user.id))
        ).all()
        existing_fronts: set[str] = set()
        existing_norms: set[str] = set()

        for note in existing_notes:
            fv = note.field_values or {}
            f = str(fv.get("Front") or fv.get("front") or fv.get("title") or "").strip()
            t = str(fv.get("title") or "").strip()
            if f:
                existing_fronts.add(f)
                existing_norms.add(norm(f))
            if t:
                existing_fronts.add(t)
                existing_norms.add(norm(t))

        log.info(f"Existing notes: {len(existing_notes)}, indexed front/title keys: {len(existing_fronts)}")

        # 3. Load master backup file
        with open(MASTER_BACKUP_PATH, "r", encoding="utf-8") as f:
            master_data = json.load(f)

        master_decks_data = master_data.get("decks", [])
        master_cards_data = master_data.get("cards", [])
        log.info(f"Master backup loaded: {len(master_decks_data)} decks, {len(master_cards_data)} cards")

        # 4. Resolve / Reconcile Deck Hierarchy
        # Root deck
        cpsc210_root = decks_by_name.get("CPSC 210")
        if cpsc210_root is None:
            cpsc210_root = decks_by_name.get("CPSC 210 — every function has a contract")
        if cpsc210_root is None:
            cpsc210_root = await ensure_deck(
                db,
                user.id,
                name="CPSC 210 — every function has a contract",
                parent_id=None,
                default_priority=80,
            )
        else:
            cpsc210_root.name = "CPSC 210 — every function has a contract"
            await db.flush()

        deck_id_map: dict[str, uuid.UUID] = {}
        # Root in master maps to cpsc210_root
        master_root_id = "118f08b61e5e4ad6927ad64c0e5c8c19"
        deck_id_map[master_root_id] = cpsc210_root.id

        # Mappings for established subtrees
        if "Lecture Activities" in decks_by_name:
            la_existing = decks_by_name["Lecture Activities"]
            for md in master_decks_data:
                if md["name"] == "Lecture Activities":
                    deck_id_map[md["id"]] = la_existing.id

        if "Labs" in decks_by_name:
            labs_existing = decks_by_name["Labs"]
            for md in master_decks_data:
                if md["name"] == "Labs":
                    deck_id_map[md["id"]] = labs_existing.id

        for i in range(1, 10):
            la_name = f"LA{i:02d}"
            if la_name in decks_by_name:
                for md in master_decks_data:
                    if md["name"] == la_name:
                        deck_id_map[md["id"]] = decks_by_name[la_name].id

        lab_name_map = {
            "Lab 1 — Reading the Tides": "Lab01 - Reading the Tides",
            "Lab 2 — Charting the Tides": "Lab02 - Charting the Tides",
            "Lab 3 — Serving the Tides": "Lab03 - Serving the Tides",
            "Lab 4 — Keeping the Tides": "Lab04 - Keeping the Tides",
        }
        for m_name, db_name in lab_name_map.items():
            if db_name in decks_by_name:
                for md in master_decks_data:
                    if md["name"] == m_name:
                        deck_id_map[md["id"]] = decks_by_name[db_name].id

        # Midterm 3 mapping
        mt3_existing = decks_by_name.get("Midterm 3") or decks_by_name.get("! Midterm 3 — Nov 13")
        if mt3_existing:
            for md in master_decks_data:
                if md["name"] == "! Midterm 3 — Nov 13":
                    deck_id_map[md["id"]] = mt3_existing.id

        log.info(f"Pre-mapped {len(deck_id_map)} master decks to existing DB decks.")

        # Build deck tree from master backup in dependency order (parents before children)
        # 1. Group master decks by parent_id
        master_by_id = {d["id"]: d for d in master_decks_data}
        unprocessed = list(master_decks_data)
        
        while unprocessed:
            progress = False
            remaining = []
            for d in unprocessed:
                did = d["id"]
                if did in deck_id_map:
                    # Already mapped
                    progress = True
                    continue
                pid = d.get("parent_id")
                if pid is None or pid in deck_id_map:
                    # Parent is mapped or None
                    mapped_parent_id = deck_id_map[pid] if pid else None
                    target_deck_uuid = uuid.UUID(hex=did)
                    
                    # Check if already exists by uuid
                    existing_d = decks_by_id.get(target_deck_uuid)
                    if existing_d:
                        deck_id_map[did] = existing_d.id
                    else:
                        new_deck = Deck(
                            id=target_deck_uuid,
                            user_id=user.id,
                            name=d["name"],
                            parent_id=mapped_parent_id,
                            default_priority=d.get("default_priority", 50),
                            documentation=d.get("documentation"),
                            thematic_nature=d.get("thematic_nature"),
                            source_documents=list(d.get("source_documents") or []),
                        )
                        db.add(new_deck)
                        await db.flush()
                        deck_id_map[did] = new_deck.id
                        decks_by_id[new_deck.id] = new_deck
                        decks_by_name[new_deck.name] = new_deck
                    progress = True
                else:
                    remaining.append(d)
            if not progress and remaining:
                log.warning(f"Could not resolve parents for {len(remaining)} decks; attaching to root")
                for d in remaining:
                    target_deck_uuid = uuid.UUID(hex=d["id"])
                    new_deck = Deck(
                        id=target_deck_uuid,
                        user_id=user.id,
                        name=d["name"],
                        parent_id=cpsc210_root.id,
                        default_priority=d.get("default_priority", 50),
                        documentation=d.get("documentation"),
                        thematic_nature=d.get("thematic_nature"),
                        source_documents=list(d.get("source_documents") or []),
                    )
                    db.add(new_deck)
                    await db.flush()
                    deck_id_map[d["id"]] = new_deck.id
                    decks_by_id[new_deck.id] = new_deck
                    decks_by_name[new_deck.name] = new_deck
                break
            unprocessed = remaining

        log.info(f"All {len(master_decks_data)} master decks resolved/created.")

        # Re-parent CPSC 210 MT3 Essentials under Midterm 3 if present
        mt3_deck_id = deck_id_map.get("df6a2dc479b14842b10a2663ce0983cb") or (mt3_existing.id if mt3_existing else None)
        if mt3_deck_id:
            mt3_essentials = decks_by_name.get("CPSC 210 MT3 Essentials")
            if mt3_essentials and mt3_essentials.parent_id != mt3_deck_id:
                mt3_essentials.parent_id = mt3_deck_id
                await db.flush()
                log.info(f"Nested 'CPSC 210 MT3 Essentials' under Midterm 3 deck.")

        # Ensure Basics Deck
        part1_deck_id = deck_id_map.get("51e040a5a0f146f8841da50ee63c9b46")
        basics_deck = await ensure_deck(
            db,
            user.id,
            name="Basics - TypeScript Foundations (Ch 1, 2, 5, 6, 10)",
            parent_id=part1_deck_id or cpsc210_root.id,
            default_priority=50,
            thematic_nature="TypeScript foundational review covering types, functions, arrays, mutation, and basic classes.",
            documentation="Foundational exercises for Midterm 3 and Final preparation.",
        )
        decks_by_name[basics_deck.name] = basics_deck

        # Ensure Final Exam Prep Decks
        final_parent_deck = await ensure_deck(
            db,
            user.id,
            name="Final Exam Prep",
            parent_id=cpsc210_root.id,
            default_priority=75,
            thematic_nature="Comprehensive CPSC 210 Final Exam synthesis across all 22 chapters.",
            documentation="Review tracks for Part 1 (Making Code Correct), Part 2 (Building Abstractions), and Part 3 (Growing Systems).",
        )
        decks_by_name[final_parent_deck.name] = final_parent_deck

        final_p1_deck = await ensure_deck(
            db,
            user.id,
            name="Final Prep 1 - Making Code Correct (Ch 3, 4, 7, 8, 9)",
            parent_id=final_parent_deck.id,
            default_priority=75,
            thematic_nature="Invariants, state maintenance, async effects, error handling, and test validation.",
        )
        final_p2_deck = await ensure_deck(
            db,
            user.id,
            name="Final Prep 2 - Building Abstractions (Ch 11-16)",
            parent_id=final_parent_deck.id,
            default_priority=75,
            thematic_nature="Decomposition, encapsulation, subtyping/LSP, boundaries, and extension.",
        )
        final_p3_deck = await ensure_deck(
            db,
            user.id,
            name="Final Prep 3 - Growing Systems (Ch 17-22)",
            parent_id=final_parent_deck.id,
            default_priority=75,
            thematic_nature="Coupling, data consumption/JSON, API design, refactoring, and debugging.",
        )
        decks_by_name[final_p1_deck.name] = final_p1_deck
        decks_by_name[final_p2_deck.name] = final_p2_deck
        decks_by_name[final_p3_deck.name] = final_p3_deck

        # NoteTypes cache
        nt_math_code = await default_note_type(db, user, "basic", grading_profile="math_code")
        nt_short_answer = await default_note_type(db, user, "basic", grading_profile="short_answer")

        # 5. Ingest Master Backup Cards
        master_imported = 0
        master_skipped = 0
        master_citations = 0

        for c_data in master_cards_data:
            fv = c_data.get("field_values") or {}
            if isinstance(fv, str):
                try:
                    fv = json.loads(fv)
                except Exception:
                    fv = {}

            front = str(fv.get("Front") or fv.get("front") or fv.get("title") or "").strip()
            title = str(fv.get("title") or "").strip()

            if not front:
                master_skipped += 1
                continue

            if front in existing_fronts or norm(front) in existing_norms or (title and (title in existing_fronts or norm(title) in existing_norms)):
                master_skipped += 1
                continue

            existing_fronts.add(front)
            existing_norms.add(norm(front))
            if title:
                existing_fronts.add(title)
                existing_norms.add(norm(title))

            # Target deck
            raw_deck_id = c_data.get("deck_id")
            target_deck_id = deck_id_map.get(raw_deck_id) or cpsc210_root.id
            target_deck = decks_by_id.get(target_deck_id)

            is_code = (
                c_data.get("card_type") == "code"
                or bool(fv.get("starter_code"))
                or bool(fv.get("test_cases"))
            )
            nt = nt_math_code if is_code else nt_short_answer

            # Standardize field_values for Ars Memoriae
            clean_fv = dict(fv)
            if "Front" not in clean_fv and "front" in clean_fv:
                clean_fv["Front"] = clean_fv.pop("front")
            elif "Front" not in clean_fv:
                clean_fv["Front"] = front
            if "Back" not in clean_fv and "back" in clean_fv:
                clean_fv["Back"] = clean_fv.pop("back")

            note = Note(
                user_id=user.id,
                note_type_id=nt.id,
                field_values=clean_fv,
            )
            db.add(note)
            await db.flush()

            tags = list(c_data.get("tags") or [])
            card_prio = c_data.get("priority")
            if card_prio is None and target_deck:
                card_prio = target_deck.default_priority

            card = Card(
                note_id=note.id,
                deck_id=target_deck_id,
                template_slot="0",
                priority=card_prio or 50,
                origin="imported",
                tags=tags,
                state=c_data.get("state") or "new",
                stability=c_data.get("stability"),
                difficulty=c_data.get("difficulty"),
                due=parse_datetime(c_data.get("due")),
                documentation=c_data.get("card_documentation") or (target_deck.documentation if target_deck else None),
                thematic_nature=target_deck.thematic_nature if target_deck else None,
                source_documents=list(target_deck.source_documents or []) if target_deck else [],
            )
            db.add(card)
            await db.flush()
            master_imported += 1

            # References / Citations
            refs = c_data.get("references") or []
            for r in refs:
                quote = str(r.get("quote") or "").strip()
                locator = str(r.get("locator") or "").strip()
                source_title = str(r.get("source_title") or "").strip()
                if quote or locator:
                    db.add(
                        CardReference(
                            card_id=card.id,
                            quote=quote or (f"Excerpt from {locator}" if locator else ""),
                            quote_verified=bool(r.get("quote_verified", True)),
                            locator=locator or None,
                            source_title=source_title or (target_deck.name if target_deck else "CPSC 210"),
                        )
                    )
                    master_citations += 1

        log.info(f"Phase 1 Complete: Ingested {master_imported} master backup cards ({master_skipped} skipped, {master_citations} citations).")

        # 6. Helper for subfolder card ingestion
        async def ingest_subfolder_notes(
            notes_list: list[dict],
            target_deck: Deck,
            default_prio: int = 50,
            default_source_file: str = "",
        ) -> tuple[int, int, int]:
            added_cnt = 0
            skipped_cnt = 0
            cites_cnt = 0
            for item in notes_list:
                front = (item.get("front") or item.get("Front") or item.get("title") or "").strip()
                back = (item.get("back") or item.get("Back") or "").strip()
                title = (item.get("title") or "").strip()

                if not front:
                    skipped_cnt += 1
                    continue

                if front in existing_fronts or norm(front) in existing_norms or (title and (title in existing_fronts or norm(title) in existing_norms)):
                    skipped_cnt += 1
                    continue

                existing_fronts.add(front)
                existing_norms.add(norm(front))
                if title:
                    existing_fronts.add(title)
                    existing_norms.add(norm(title))

                is_code = (
                    item.get("card_type") == "code"
                    or bool(item.get("starter_code"))
                    or bool(item.get("test_cases"))
                )

                field_values: dict = {"Front": front, "Back": back}
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

                nt = nt_math_code if is_code else nt_short_answer
                note = Note(user_id=user.id, note_type_id=nt.id, field_values=field_values)
                db.add(note)
                await db.flush()

                tags = list(item.get("tags") or [])
                if is_code and "code" not in tags:
                    tags.append("code")

                card_prio = item.get("priority") if item.get("priority") is not None else default_prio

                quote = (item.get("quote") or "").strip()
                locator = (item.get("locator") or "").strip()

                doc_parts = []
                if locator:
                    doc_parts.append(f"**Locator**: {locator}")
                if quote:
                    doc_parts.append(f"**Key Quote**: \"{quote}\"")
                card_doc = "\n\n".join(doc_parts) if doc_parts else target_deck.documentation

                card_sources = [
                    {
                        "name": "CPSC210_2026W1_Master.pdf",
                        "locator": locator,
                        "quote": quote,
                        "source_file": default_source_file,
                    }
                ] if locator or quote else target_deck.source_documents

                card = Card(
                    note_id=note.id,
                    deck_id=target_deck.id,
                    template_slot="0",
                    priority=card_prio,
                    origin="imported",
                    tags=tags,
                    state="new",
                    documentation=card_doc,
                    thematic_nature=item.get("category") or target_deck.thematic_nature,
                    source_documents=list(card_sources or []),
                )
                db.add(card)
                await db.flush()
                added_cnt += 1

                if quote or locator:
                    db.add(
                        CardReference(
                            card_id=card.id,
                            quote=quote or (f"Excerpt from {locator}" if locator else ""),
                            quote_verified=True,
                            locator=locator or None,
                            source_title=item.get("source_title") or f"CPSC 210 — {target_deck.name}",
                        )
                    )
                    cites_cnt += 1

            return added_cnt, skipped_cnt, cites_cnt

        # 7. Ingest Subfolders
        subfolder_report = []

        # Find Ch 08 & Ch 09 decks
        ch08_deck = decks_by_name.get("Ch 08: Designing for Failure")
        ch09_deck = decks_by_name.get("Ch 09: Validating Behaviour")

        # 7A. 3 - Textbook Ch1-7
        tb_dir = SOURCE_ROOT / "3 - Textbook Ch1-7"
        if tb_dir.exists():
            for fname in os.listdir(tb_dir):
                if not fname.endswith(".json") or fname.endswith("_wrapped.json"):
                    continue
                fpath = tb_dir / fname
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                notes = data if isinstance(data, list) else data.get("notes", [])

                # Route to proper deck
                t_deck = None
                if "ch8" in fname or "ch08" in fname:
                    t_deck = ch08_deck
                elif "ch9" in fname or "ch09" in fname:
                    t_deck = ch09_deck
                else:
                    # Ch1-Ch7
                    for num in range(1, 8):
                        if f"ch{num}" in fname:
                            for dname, d_obj in decks_by_name.items():
                                if f"Ch 0{num}" in dname or f"Ch {num}" in dname:
                                    t_deck = d_obj
                                    break
                            break

                if t_deck is None:
                    t_deck = cpsc210_root

                a, s, c = await ingest_subfolder_notes(
                    notes, t_deck, default_prio=50, default_source_file=fname
                )
                subfolder_report.append({"folder": "3 - Textbook Ch1-7", "file": fname, "deck": t_deck.name, "added": a, "skipped": s})

        # 7B. 7 - Basics
        basics_file = SOURCE_ROOT / "7 - Basics" / "cpsc210_basics_foundations.json"
        if basics_file.exists():
            with open(basics_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            notes = data if isinstance(data, list) else data.get("notes", [])
            a, s, c = await ingest_subfolder_notes(
                notes, basics_deck, default_prio=50, default_source_file=basics_file.name
            )
            subfolder_report.append({"folder": "7 - Basics", "file": basics_file.name, "deck": basics_deck.name, "added": a, "skipped": s})

        # 7C. 8 - Final
        final_dir = SOURCE_ROOT / "8 - Final"
        final_files_map = {
            "cpsc210_final_p1_making_code_correct.json": final_p1_deck,
            "cpsc210_final_p2_building_abstractions.json": final_p2_deck,
            "cpsc210_final_p3_growing_systems.json": final_p3_deck,
        }
        for fname, f_deck in final_files_map.items():
            fpath = final_dir / fname
            if fpath.exists():
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                notes = data if isinstance(data, list) else data.get("notes", [])
                a, s, c = await ingest_subfolder_notes(
                    notes, f_deck, default_prio=75, default_source_file=fname
                )
                subfolder_report.append({"folder": "8 - Final", "file": fname, "deck": f_deck.name, "added": a, "skipped": s})

        # 7D. Check all other folders (1 - LA decks, 2 - Supplemental, 4 - Piazza, 5 - MT3, 6 - Labs)
        other_folders = ["1 - LA decks", "2 - Supplemental", "4 - Piazza high-yield", "5 - MT3", "6 - Labs"]
        for of in other_folders:
            odir = SOURCE_ROOT / of
            if not odir.exists():
                continue
            for fname in os.listdir(odir):
                if not fname.endswith(".json") or fname.endswith("_wrapped.json"):
                    continue
                fpath = odir / fname
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                notes = data if isinstance(data, list) else data.get("notes", [])
                
                # Best effort deck routing for any leftover cards
                t_deck = cpsc210_root
                if of == "1 - LA decks":
                    m_la = re.search(r"LA(\d+)", fname)
                    if m_la:
                        la_num = f"LA{int(m_la.group(1)):02d}"
                        t_deck = decks_by_name.get(la_num, cpsc210_root)
                elif of == "6 - Labs":
                    for k, v in lab_name_map.items():
                        if k[:5].lower() in fname.lower() or v[:5].lower() in fname.lower():
                            t_deck = decks_by_name.get(v, cpsc210_root)
                            break
                elif of == "5 - MT3":
                    for dname, d_obj in decks_by_name.items():
                        for ch in range(8, 17):
                            if f"ch{ch:02d}" in fname and f"Ch {ch:02d}" in dname:
                                t_deck = d_obj
                                break

                a, s, c = await ingest_subfolder_notes(
                    notes, t_deck, default_prio=50, default_source_file=fname
                )
                if a > 0 or s > 0:
                    subfolder_report.append({"folder": of, "file": fname, "deck": t_deck.name, "added": a, "skipped": s})

        # 8. Record in imports table
        total_new_imported = master_imported + sum(r["added"] for r in subfolder_report)
        db.add(
            Import(
                user_id=user.id,
                filename="cpsc210_all_subtrees_master",
                notes_mapped=total_new_imported,
                cards_mapped=total_new_imported,
                warnings=[],
            )
        )
        await db.commit()
        log.info(f"Cards transaction committed. Total new cards ingested: {total_new_imported}")

        # 9. Sync Knowledge Nodes Tree
        log.info("Synchronizing Knowledge Nodes tree...")
        await ensure_tree(db, user)
        await db.commit()
        log.info("Knowledge tree synchronized successfully.")

        return {
            "master_cards_imported": master_imported,
            "master_cards_skipped": master_skipped,
            "master_citations": master_citations,
            "subfolders_summary": subfolder_report,
            "total_new_cards": total_new_imported,
        }


if __name__ == "__main__":
    report = asyncio.run(run_import())
    print("\n=== IMPORT COMPLETE ===")
    print(json.dumps(report, indent=2))
