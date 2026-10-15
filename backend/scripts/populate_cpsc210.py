"""Populate complete CPSC 210 hierarchy and import existing cards with full documentation attribution."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select

from app.db import SessionLocal
from app.models import (
    Deck,
    Import,
    User,
)
from scripts.cpsc210_ingest import all_user_fronts
from scripts.cpsc210_ingest import ingest_notes_list as shared_ingest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

USER_EMAIL = "michael.r.polley@outlook.com"
CARDS_DOCUMENTS_DIR = r"C:\Users\micha\OneDrive\Documents\UBC BCS ICS\CPSC 210\Cards\Cards Documents"
CARDS_SOURCE_DIR = r"C:\Users\micha\OneDrive\Documents\UBC BCS ICS\CPSC 210\Cards\Cards"
OBSIDIAN_SPEC = r"C:\Syncthing Obsidian\CPSC 210.md"
MASTER_PDF_PATH = r"C:\Users\micha\OneDrive\Documents\UBC BCS ICS\CPSC 210\Cards\Cards Documents\CPSC210_2026W1_Master.pdf"

HIERARCHY_TREE = {
    "name": "CPSC 210 — every function has a contract",
    "thematic_nature": "Every function has a contract: preconditions, postconditions, and invariants. Software construction is the disciplined enforcement, abstraction, and maintenance of these contracts across changing requirements.",
    "target_event_title": "Final Exam",
    "target_event_date": "2026-12-15T12:00:00",
    "documentation": (
        "Core course hierarchy for UBC CPSC 210 (Software Construction in TypeScript).\n"
        "Guiding principle: Every function has a contract.\n"
        "Key evaluation milestones: Midterm 1, Midterm 2, Midterm 3 (Nov 13), and Final Exam (Dec 11–22).\n"
        "Resources: Official Course Textbook, PrairieLearn Lecture Activities (LA01–LA22), and Labs 1–8."
    ),
    "source_documents": [
        {"name": "CPSC210_2026W1_Master.pdf", "path": MASTER_PDF_PATH, "type": "syllabus_and_textbook", "pages": "1-498"},
        {"name": "CPSC 210.md", "path": OBSIDIAN_SPEC, "type": "study_tree_and_roadmap"},
    ],
    "children": [
        {
            "name": "Part 1: Foundations — keep the contract",
            "thematic_nature": "Foundations: Keeping contracts at the function and module level using TypeScript types, assertions, equivalence partitions, and asynchronous event loops.",
            "target_event_title": "MT1 ✔ · MT2 ✔ · Final",
            "documentation": "Chapters 01 to 09. Scope for Midterm 1, Midterm 2, and Final Exam. Focus: Keeping the contract.",
            "source_documents": [
                {"name": "CPSC210_2026W1_Master.pdf", "path": MASTER_PDF_PATH, "type": "textbook", "pages": "11-211"},
                {"name": "Lecture Activities LA01–LA09", "path": os.path.join(CARDS_DOCUMENTS_DIR, "LA's"), "type": "assignment_specs"},
                {"name": "Labs 1–4", "path": os.path.join(CARDS_DOCUMENTS_DIR, "Labs"), "type": "lab_specs"},
            ],
            "chapters": [
                {
                    "num": 1,
                    "name": "Ch 01: Learning a New Language",
                    "thematic_nature": "TypeScript Syntax, Functions, Return Types, and Primitives.",
                    "documentation": "Basic types (number, string, boolean), functions, control flow (if/else return order), compiler vs runtime. Tested on MT1, MT2, Final.",
                    "pages": "16-40",
                    "la": "LA01.1-full-assignment.md",
                    "lab": "Lab01.1-full-assignment.md (Single Tide Station)",
                },
                {
                    "num": 2,
                    "name": "Ch 02: Modelling With Types",
                    "thematic_nature": "Type Aliases, Union Types, Discriminated Unions, and Compile-Time Contracts.",
                    "documentation": "Modelling domain concepts with discrete types, string literal unions, and records. Tested on MT1, MT2, Final.",
                    "pages": "41-63",
                    "la": "LA02.1-full-assignment.md",
                    "lab": "Lab01.1-full-assignment.md",
                },
                {
                    "num": 3,
                    "name": "Ch 03: Checking Invariants",
                    "thematic_nature": "Preconditions, Equivalence Class Partitioning, Boundary Value Analysis & Assertions.",
                    "documentation": "Contract validation with assert(), testing boundaries (at, just above, just below), invalid input handling. Tested on MT1, MT2, Final.",
                    "pages": "64-86",
                    "la": "LA03.1-full-assignment.md",
                    "lab": "Lab01.1-full-assignment.md",
                },
                {
                    "num": 4,
                    "name": "Ch 04: Maintaining Invariants",
                    "thematic_nature": "State Invariants, Constructor Validation, and Closure Encapsulation.",
                    "documentation": "Establishing invariants in constructors, preserving invariants across state transitions, preventing invalid state. Tested on MT1, MT2, Final.",
                    "pages": "87-101",
                    "la": "LA04.1-full-assignment.md",
                    "lab": "Lab01.1-full-assignment.md",
                },
                {
                    "num": 5,
                    "name": "Ch 05: Arrays and Iteration",
                    "thematic_nature": "Array Processing, Loop Invariants, and Higher-Order Iteration (map/filter/reduce).",
                    "documentation": "Sequences, bounds checking, transform pipelines, debug practice on indexing off-by-one errors. Tested on MT2, Final.",
                    "pages": "102-119",
                    "la": "LA05.1-full-assignment.md",
                    "lab": "Lab02.1-full-assignment.md (Multiple Tide Stations)",
                },
                {
                    "num": 6,
                    "name": "Ch 06: Mutation and Side Effects",
                    "thematic_nature": "Object References, Aliasing Pitfalls, Shallow vs Deep Copy, Pure Functions.",
                    "documentation": "Memory models, reference sharing, unexpected mutation side-effects, immutable design. Tested on MT2, Final.",
                    "pages": "120-142",
                    "la": "LA06.1-full-assignment.md",
                    "lab": "Lab02.1-full-assignment.md",
                },
                {
                    "num": 7,
                    "name": "Ch 07: Asynchronous Effects",
                    "thematic_nature": "JavaScript Event Loop, Promises, and async/await Execution Contracts.",
                    "documentation": "Asynchronous effects, Promise resolution/rejection, async/await, non-blocking I/O. Tested on MT2, Final.",
                    "pages": "143-168",
                    "la": "LA07.1-full-assignment.md",
                    "lab": "Lab03.1-full-assignment.md (Serving the Tides)",
                },
                {
                    "num": 8,
                    "name": "Ch 08: Designing for Failure",
                    "thematic_nature": "Result<T, E> Monad Pattern vs Exceptions, Recoverable Error Contracts.",
                    "documentation": "Explicit error return with Result<T, E>, distinguishing programming bugs (assert) from recoverable failures (Result). Tested on MT3, Final.",
                    "pages": "169-192",
                    "la": "LA08.1-full-assignment.md",
                    "lab": "Lab03.1 & Lab04.1",
                },
                {
                    "num": 9,
                    "name": "Ch 09: Validating Behaviour",
                    "thematic_nature": "Test Suite Strength, Reference Test Suites, Fault Injection & Property Testing.",
                    "documentation": "Ensuring test suites catch faulty implementations without producing false alarms. Tested on MT3, Final.",
                    "pages": "193-211",
                    "la": "LA09.1-full-assignment.md",
                    "lab": "Lab03.1-full-assignment.md",
                },
            ],
        },
        {
            "name": "Part 2: Abstraction — hide behind the contract",
            "thematic_nature": "Abstraction: Hiding representation and variability behind interfaces, abstract types, and polymorphic boundaries.",
            "target_event_title": "Midterm 3",
            "target_event_date": "2026-11-13T14:00:00",
            "documentation": "Chapters 10 to 16. Scope for Midterm 3 (Nov 13) and Final Exam. Focus: Hide behind the contract.",
            "source_documents": [
                {"name": "CPSC210_2026W1_Master.pdf", "path": MASTER_PDF_PATH, "type": "textbook", "pages": "212-320"},
            ],
            "chapters": [
                {
                    "num": 10,
                    "name": "Ch 10: Building Abstractions",
                    "thematic_nature": "Procedural and Data Abstraction, Abstract Data Types, Information Hiding.",
                    "documentation": "Separating interface from implementation, clients depend only on contracts. Tested on MT3, Final.",
                    "pages": "216-233",
                    "la": "LA10 (PrairieLearn)",
                    "lab": "Lab 5 (Ferry Scheduling)",
                },
                {
                    "num": 11,
                    "name": "Ch 11: Decomposing Systems",
                    "thematic_nature": "Modular Decomposition, High Cohesion, and Subsystem Responsibilities.",
                    "documentation": "Factoring complex problems into cohesive, loosely coupled units. Tested on MT3, Final.",
                    "pages": "234-244",
                    "la": "LA11",
                    "lab": "Lab 5",
                },
                {
                    "num": 12,
                    "name": "Ch 12: Encapsulating What Varies",
                    "thematic_nature": "Encapsulation, Strategy Pattern, Isolating Volatile Requirements.",
                    "documentation": "Hiding implementation variability behind uniform interfaces so callers remain unchanged. Tested on MT3, Final.",
                    "pages": "245-263",
                    "la": "LA12",
                    "lab": "Lab 5",
                },
                {
                    "num": 13,
                    "name": "Ch 13: Implementation Freedom",
                    "thematic_nature": "Liskov Substitution Principle, Subtyping, and Representation Independence.",
                    "documentation": "Allowing alternative implementations to satisfy the same specification. Tested on MT3, Final.",
                    "pages": "264-278",
                    "la": "LA13",
                    "lab": "Lab 6 (Ferry Reservations)",
                },
                {
                    "num": 14,
                    "name": "Ch 14: Defining Boundaries",
                    "thematic_nature": "Module Boundaries, Export Surfaces, and Visibility Modifiers.",
                    "documentation": "Public vs private APIs, defining clean surface boundaries. Tested on MT3, Final.",
                    "pages": "279-291",
                    "la": "LA14",
                    "lab": "Lab 6",
                },
                {
                    "num": 15,
                    "name": "Ch 15: Extending Behaviour",
                    "thematic_nature": "Polymorphism, Composition over Inheritance, and Template Methods.",
                    "documentation": "Extending existing behavior safely without modifying base contract semantics. Tested on MT3, Final.",
                    "pages": "292-306",
                    "la": "LA15",
                    "lab": "Lab 6",
                },
                {
                    "num": 16,
                    "name": "Ch 16: Growing Systems",
                    "thematic_nature": "Extensible Architectures, Open/Closed Principle, Design Review.",
                    "documentation": "Structuring codebases to scale cleanly with evolving requirements. Tested on MT3, Final.",
                    "pages": "307-320",
                    "la": "LA16",
                    "lab": "Solo Project",
                },
            ],
        },
        {
            "name": "Part 3: Evolution — keep contracts stable",
            "thematic_nature": "Evolution: Preserving contract stability during coupling refactoring, data consumption, API evolution, and debugging.",
            "target_event_title": "Final Exam",
            "target_event_date": "2026-12-15T12:00:00",
            "documentation": "Chapters 17 to 22. Scope for Final Exam. Focus: Keep contracts stable.",
            "source_documents": [
                {"name": "CPSC210_2026W1_Master.pdf", "path": MASTER_PDF_PATH, "type": "textbook", "pages": "321-434"},
            ],
            "chapters": [
                {
                    "num": 17,
                    "name": "Ch 17: Coupling",
                    "thematic_nature": "Loose Coupling, Dependency Injection, Minimizing Inter-Module Ties.",
                    "documentation": "Measuring and reducing coupling to make changes localized and safe. Tested on Final.",
                    "pages": "325-348",
                    "la": "LA17",
                    "lab": "Lab 7 (Fixing Problems)",
                },
                {
                    "num": 18,
                    "name": "Ch 18: Consuming Data",
                    "thematic_nature": "Data Serialization, JSON Deserialization, Schema Validation & DTOs.",
                    "documentation": "Safely consuming untrusted external data and mapping to typed internal models. Tested on Final.",
                    "pages": "349-372",
                    "la": "LA18",
                    "lab": "Labs 3–4",
                },
                {
                    "num": 19,
                    "name": "Ch 19: Designing APIs",
                    "thematic_nature": "REST Principles, HTTP Verbs, Idempotency, and API Contract Design.",
                    "documentation": "Designing intuitive, predictable interfaces for web clients and servers. Tested on Final.",
                    "pages": "373-387",
                    "la": "LA19",
                    "lab": "Labs 3–4",
                },
                {
                    "num": 20,
                    "name": "Ch 20: Code Quality and Refactoring",
                    "thematic_nature": "Code Smells, Clean Code, Refactoring Patterns, Behavior Preservation.",
                    "documentation": "Refactoring code structure systematically while keeping all tests passing. Tested on Final.",
                    "pages": "388-403",
                    "la": "LA20",
                    "lab": "Lab 7",
                },
                {
                    "num": 21,
                    "name": "Ch 21: Debugging",
                    "thematic_nature": "Scientific Debugging Method, Hypothesis Testing, Reproducible Reproductions.",
                    "documentation": "Isolating root causes, minimizing failing test cases, regression guarding. Tested on Final.",
                    "pages": "404-418",
                    "la": "LA21",
                    "lab": "Lab 7",
                },
                {
                    "num": 22,
                    "name": "Ch 22: Adding New Features",
                    "thematic_nature": "Incremental Evolution, Backward Compatibility, Non-Breaking Extensions.",
                    "documentation": "Adding features to mature systems without breaking caller expectations. Tested on Final.",
                    "pages": "419-434",
                    "la": "LA22",
                    "lab": "Lab 8 (Adding Features)",
                },
            ],
        },
    ],
}


async def run_population():
    async with SessionLocal() as db:
        # 1. Fetch user
        user = await db.scalar(select(User).where(User.email == USER_EMAIL))
        if not user:
            logger.error(f"User {USER_EMAIL} not found!")
            return

        logger.info(f"Target user: {user.email} (id={user.id})")

        # 2. Check if CPSC 210 root deck already exists
        root_deck = await db.scalar(
            select(Deck).where(Deck.user_id == user.id, Deck.name == HIERARCHY_TREE["name"])
        )
        if root_deck:
            logger.info(f"Root deck '{root_deck.name}' already exists (id={root_deck.id}).")
        else:
            root_deck = Deck(
                user_id=user.id,
                name=HIERARCHY_TREE["name"],
                parent_id=None,
                default_priority=50,
                thematic_nature=HIERARCHY_TREE["thematic_nature"],
                documentation=HIERARCHY_TREE["documentation"],
                source_documents=HIERARCHY_TREE["source_documents"],
                target_event_title=HIERARCHY_TREE["target_event_title"],
                target_event_date=datetime.fromisoformat(HIERARCHY_TREE["target_event_date"]),
            )
            db.add(root_deck)
            await db.flush()
            logger.info(f"Created Root deck: {root_deck.name} (id={root_deck.id})")

        # 3. Create Part decks and Chapter subdecks
        chapter_deck_map: dict[int, Deck] = {}
        part_deck_map: dict[str, Deck] = {}

        for part_info in HIERARCHY_TREE["children"]:
            part_name = part_info["name"]
            part_deck = await db.scalar(
                select(Deck).where(Deck.user_id == user.id, Deck.name.in_([part_name, "! " + part_name]))
            )
            if not part_deck:
                dt = (
                    datetime.fromisoformat(part_info["target_event_date"])
                    if "target_event_date" in part_info
                    else None
                )
                part_deck = Deck(
                    user_id=user.id,
                    name=part_name,
                    parent_id=root_deck.id,
                    default_priority=50,
                    thematic_nature=part_info["thematic_nature"],
                    documentation=part_info["documentation"],
                    source_documents=part_info["source_documents"],
                    target_event_title=part_info.get("target_event_title"),
                    target_event_date=dt,
                )
                db.add(part_deck)
                await db.flush()
                logger.info(f"  Created Part deck: {part_name} (id={part_deck.id})")
            part_deck_map[part_name] = part_deck

            # Create chapters for this part
            for ch in part_info.get("chapters", []):
                ch_num = ch["num"]
                ch_name = ch["name"]
                ch_deck = await db.scalar(
                    select(Deck).where(Deck.user_id == user.id, Deck.name.in_([ch_name, "! " + ch_name]))
                )
                if not ch_deck:
                    sources = [
                        {
                            "name": "CPSC210_2026W1_Master.pdf",
                            "path": MASTER_PDF_PATH,
                            "type": "textbook",
                            "pages": ch["pages"],
                        }
                    ]
                    if ch.get("la"):
                        sources.append(
                            {
                                "name": ch["la"],
                                "path": os.path.join(CARDS_DOCUMENTS_DIR, "LA's", ch["la"])
                                if os.path.exists(os.path.join(CARDS_DOCUMENTS_DIR, "LA's", ch["la"]))
                                else ch["la"],
                                "type": "assignment_spec",
                            }
                        )
                    if ch.get("lab"):
                        sources.append(
                            {
                                "name": ch["lab"],
                                "path": os.path.join(CARDS_DOCUMENTS_DIR, "Labs", ch["lab"])
                                if os.path.exists(os.path.join(CARDS_DOCUMENTS_DIR, "Labs", ch["lab"]))
                                else ch["lab"],
                                "type": "lab_spec",
                            }
                        )
                    ch_deck = Deck(
                        user_id=user.id,
                        name=ch_name,
                        parent_id=part_deck.id,
                        default_priority=50,
                        thematic_nature=ch["thematic_nature"],
                        documentation=ch["documentation"],
                        source_documents=sources,
                        target_event_title=part_deck.target_event_title,
                        target_event_date=part_deck.target_event_date,
                    )
                    db.add(ch_deck)
                    await db.flush()
                    logger.info(f"    Created Chapter deck: {ch_name} (id={ch_deck.id})")
                chapter_deck_map[ch_num] = ch_deck

        await db.commit()
        logger.info(f"Successfully configured 26-deck tree! (Total chapters registered: {len(chapter_deck_map)})")

        # 4. Ingest Flashcards into Chapter Decks (Ch 1–7)
        tb_dir = Path(CARDS_SOURCE_DIR) / "3 - Textbook Ch1-7"
        la_dir = Path(CARDS_SOURCE_DIR) / "1 - LA decks"
        supp_dir = Path(CARDS_SOURCE_DIR) / "2 - Supplemental"
        piazza_dir = Path(CARDS_SOURCE_DIR) / "4 - Piazza high-yield"

        ch_mapping = {
            1: [
                tb_dir / "cpsc210_ch1_learning_a_new_programming_language.json",
                la_dir / "cpsc210_mt2_LA01.json",
            ],
            2: [
                tb_dir / "cpsc210_ch2_using_types_to_model_problems.json",
                la_dir / "cpsc210_mt2_LA02.json",
            ],
            3: [
                tb_dir / "cpsc210_ch3_checking_invariants.json",
                la_dir / "cpsc210_mt2_LA03.json",
            ],
            4: [
                tb_dir / "cpsc210_ch4_maintaining_invariants.json",
                la_dir / "cpsc210_mt2_LA04.json",
            ],
            5: [
                tb_dir / "cpsc210_ch5_arrays_and_iteration.json",
                la_dir / "cpsc210_mt2_LA05.json",
            ],
            6: [
                tb_dir / "cpsc210_ch6_mutation_and_side_effects.json",
                la_dir / "cpsc210_mt2_LA06.json",
            ],
            7: [
                tb_dir / "cpsc210_ch7_asynchronous_effects_and_time.json",
                la_dir / "cpsc210_mt2_LA07.json",
            ],
        }

        total_notes = 0
        total_cards = 0
        total_citations = 0

        async def ingest_notes_list(notes_raw: list[dict], target_deck: Deck, source_label: str):
            """Thin wrapper over the shared helper (scripts/cpsc210_ingest.py); skips notes already in the deck."""
            nonlocal total_notes, total_cards, total_citations
            res = await shared_ingest(db, user, notes_raw, target_deck, source_label,
                                      seen_fronts=await all_user_fronts(db, user))
            total_notes += res.notes
            total_cards += res.cards
            total_citations += res.citations
            return res.cards

        # Ingest Chapters 1 to 7
        for ch_num, file_list in ch_mapping.items():
            dest_deck = chapter_deck_map[ch_num]
            for file_path in file_list:
                if not file_path.exists():
                    logger.warning(f"File not found: {file_path}")
                    continue
                with open(file_path, encoding="utf-8") as fh:
                    raw_content = json.load(fh)
                notes_data = raw_content if isinstance(raw_content, list) else raw_content.get("notes", [])
                cnt = await ingest_notes_list(notes_data, dest_deck, file_path.name)
                logger.info(f"Ch {ch_num:02d}: Imported {cnt} cards from {file_path.name}")

        # Ingest Supplemental & Piazza cards into Part 1 deck
        part1_deck = part_deck_map["Part 1: Foundations — keep the contract"]

        supp_path = supp_dir / "cpsc210_mt2_supplemental.json"
        if supp_path.exists():
            with open(supp_path, encoding="utf-8") as fh:
                raw_supp = json.load(fh)
            notes_data = raw_supp if isinstance(raw_supp, list) else raw_supp.get("notes", [])
            cnt = await ingest_notes_list(notes_data, part1_deck, supp_path.name)
            logger.info(f"Part 1: Imported {cnt} supplemental cards from {supp_path.name}")

        piazza_path = piazza_dir / "cpsc210_mt2_piazza_highyield.json"
        if piazza_path.exists():
            with open(piazza_path, encoding="utf-8") as fh:
                raw_piazza = json.load(fh)
            notes_data = raw_piazza if isinstance(raw_piazza, list) else raw_piazza.get("notes", [])
            cnt = await ingest_notes_list(notes_data, part1_deck, piazza_path.name)
            logger.info(f"Part 1: Imported {cnt} high-yield Piazza cards from {piazza_path.name}")

        import_log = Import(
            user_id=user.id,
            filename="cpsc210:complete_import",
            notes_mapped=total_notes,
            cards_mapped=total_cards,
            warnings=[],
        )
        db.add(import_log)
        await db.commit()

        logger.info("==================================================================")
        logger.info("CPSC 210 IMPORT COMPLETE!")
        logger.info(f"Total Notes created: {total_notes}")
        logger.info(f"Total Cards created: {total_cards}")
        logger.info(f"Total Citations created: {total_citations}")
        logger.info("==================================================================")


if __name__ == "__main__":
    asyncio.run(run_population())
