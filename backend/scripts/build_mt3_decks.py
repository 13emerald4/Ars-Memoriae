"""Build the "Midterm 3 — Nov 13" study tree for CPSC 210 and clean up Part 1.

What it does (idempotent; safe to re-run):

1. Creates "Midterm 3 — Nov 13" under the CPSC 210 root, next to the Parts, and moves
   Ch 08–16 into it (Ch 08/09 from Part 1, Ch 10–16 from Part 2). Every MT3 deck gets the
   MT3 target date so Event Horizon compresses intervals toward Nov 13.
2. Replaces the old Ch 08/09 cards (only notes that were never reviewed) with the rebuilt
   sets, and ingests textbook cards for Ch 10–16 from ``Cards/5 - MT3/*.json``.
3. Copies the Part 1 cards MT3 still depends on into "MT3 · Carry-forward (copies)".
   Originals stay in Part 1 untouched.
4. Part 1 cleanup: moves Piazza/supplemental cards from the Part 1 parent deck into their
   chapter decks, and suspends (never deletes) the weaker card of each duplicate group.
5. Writes a "Missing for full coverage" block into each deck's documentation and keeps the
   "! " name prefix exactly while that block lists a missing file.

Usage (from the backend folder, backend stopped):
    .venv\\Scripts\\python.exe scripts\\build_mt3_decks.py --dry-run
    .venv\\Scripts\\python.exe scripts\\build_mt3_decks.py
    .venv\\Scripts\\python.exe scripts\\build_mt3_decks.py --refresh-docs        # after adding LA/Lab specs
    .venv\\Scripts\\python.exe scripts\\build_mt3_decks.py --chapter 10          # ingest new JSON for one chapter
    .venv\\Scripts\\python.exe scripts\\build_mt3_decks.py --revert-structure    # after Nov 13
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import delete, func, select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import Card, Deck, Note, ReviewLog, User  # noqa: E402
from scripts.cpsc210_ingest import ingest_notes_list  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("build_mt3")

USER_EMAIL = "michael.r.polley@outlook.com"
CARDS_ROOT = Path(r"C:\Users\micha\OneDrive\Documents\UBC BCS ICS\CPSC 210\Cards")

ROOT_NAME = "CPSC 210 — every function has a contract"
PART1 = "Part 1: Foundations — keep the contract"
PART2 = "Part 2: Abstraction — hide behind the contract"
PART3 = "Part 3: Evolution — keep contracts stable"
MT3_NAME = "Midterm 3 — Nov 13"
CARRY_NAME = "MT3 · Carry-forward (copies)"
MT3_TITLE = "Midterm 3"
MT3_DATE = datetime(2026, 11, 13, 14, 0, 0)
MT3_PRIORITY = 80
# Priority tiers inside every MT3 chapter (and the carry-forward deck). Each card JSON item carries
# "tier": 1-3; cards are moved into the matching subdeck and given that tier's priority.
CODING_NAME = "Coding drills"   # every code + test-writing MT3 card, one subdeck per chapter
CODING_PRIORITY = 90
TIERS = {
    1: ("P1 — Most likely tested", 90),
    2: ("P2 — Supporting concepts", 70),
    3: ("P3 — Background", 40),
}
MISSING_MARK = "⚠ "
NEEDS = re.compile(r"\[needs: ([^\]]+)\]")

# chapter number -> deck name, description, textbook pages, required specs (relative to Cards Documents)
CHAPTERS: dict[int, dict] = {
    8: dict(name="Ch 08: Designing for Failure", pages="169-192",
            theme="Expected vs unexpected errors; returning Result vs throwing; try/catch/finally.",
            doc="Expected vs unexpected errors, Result<T, E> vs exceptions, try/catch/finally, propagation "
                "through the call stack, where to catch, never swallowing errors. LA08: file-import pipeline. "
                "Tested on MT3 and the Final.",
            needs=[("LA's/LA08.1-full-assignment.md", "LA08.1 spec")]),
    9: dict(name="Ch 09: Validating Behaviour", pages="193-211",
            theme="chai expect vocabulary, layered assertions, input/output partitioning, coverage, regression.",
            doc="chai/vitest assertions (equal vs deep.equal, to.throw, closeTo), layered assertions, partitioning "
                "composite inputs and outputs, white-box testing and branch coverage, regression testing. LA09: "
                "reactor test-suite strength (mutation grading). Tested on MT3 and the Final.",
            needs=[("LA's/LA09.1-full-assignment.md", "LA09.1 spec")]),
    10: dict(name="Ch 10: Building Abstractions", pages="216-233",
             theme="Classes bundle state with the operations that maintain it.",
             doc="Classes vs closures, fields/constructors/methods/this/new, classes as types, objects and "
                 "references, testing classes with beforeEach. Tested on MT3 and the Final.",
             needs=[("LA's/LA10.1-full-assignment.md", "LA10.1 spec (PrairieLearn)"),
                    ("Labs/Lab05.1-full-assignment.md", "Lab 5 — Ferry Scheduling spec")]),
    11: dict(name="Ch 11: Decomposing Systems", pages="234-244",
             theme="Cohesion: one class, one invariant; composition and delegation.",
             doc="Cohesion, god classes, the Single Responsibility Principle, diagnosing a class, designing a "
                 "decomposition, composition and delegation, judgment-call splits. Tested on MT3 and the Final.",
             needs=[("LA's/LA11.1-full-assignment.md", "LA11.1 spec (PrairieLearn)"),
                    ("Labs/Lab05.1-full-assignment.md", "Lab 5 — Ferry Scheduling spec")]),
    12: dict(name="Ch 12: Encapsulating What Varies", pages="245-263",
             theme="private/readonly, defensive copying, changing the representation, testability.",
             doc="public/private/readonly, validating constructors, escaping references and defensive copies, "
                 "Array→Set representation change, Set/Map, controllability and observability. Tested on MT3 "
                 "and the Final.",
             needs=[("LA's/LA12.1-full-assignment.md", "LA12.1 spec (PrairieLearn)"),
                    ("Labs/Lab05.1-full-assignment.md", "Lab 5 — Ferry Scheduling spec")]),
    13: dict(name="Ch 13: Implementation Freedom", pages="264-278",
             theme="Representation vs abstract value; equality, immutability, generics.",
             doc="Abstract values and the abstraction function, identity vs equivalence (equals), comparing at "
                 "the right level, immutability and value objects, generic classes and what flexibility costs. "
                 "Tested on MT3 and the Final.",
             needs=[("LA's/LA13.1-full-assignment.md", "LA13.1 spec (PrairieLearn)"),
                    ("Labs/Lab06.1-full-assignment.md", "Lab 6 — Ferry Reservations spec")]),
    14: dict(name="Ch 14: Defining Boundaries", pages="279-291",
             theme="Interfaces, apparent vs actual types, test doubles, small contracts.",
             doc="interface and implements, structural typing, apparent vs actual types, program to an "
                 "interface, test doubles, interface segregation, constraining type parameters. Tested on MT3 "
                 "and the Final.",
             needs=[("LA's/LA14.1-full-assignment.md", "LA14.1 spec (PrairieLearn)"),
                    ("Labs/Lab06.1-full-assignment.md", "Lab 6 — Ferry Reservations spec")]),
    15: dict(name="Ch 15: Extending Behaviour", pages="292-306",
             theme="Abstract base classes, overriding, dynamic dispatch, substitutability.",
             doc="Abstract classes, extends/override/super, protected, polymorphism and dynamic dispatch, "
                 "demanding no more and promising no less, is-a vs can-do, composition over inheritance, "
                 "fragile base classes. Tested on MT3 and the Final.",
             needs=[("LA's/LA15.1-full-assignment.md", "LA15.1 spec (PrairieLearn)"),
                    ("Labs/Lab06.1-full-assignment.md", "Lab 6 — Ferry Reservations spec")]),
    16: dict(name="Ch 16: Growing Systems", pages="307-320",
             theme="Open/Closed Principle; choosing the axis of change.",
             doc="Open for extension, closed for modification; plugin architecture; axis of change and "
                 "speculative generality; how the Part 2 principles combine. Tested on MT3 and the Final.",
             needs=[("LA's/LA16.1-full-assignment.md", "LA16.1 spec (PrairieLearn)")]),
}
# Part 3 chapters keep their "!" until their specs exist and cards are built.
PART3_NEEDS: dict[str, list[tuple[str, str]]] = {
    "Ch 17: Coupling": [("LA's/LA17.1-full-assignment.md", "LA17.1 spec"), ("Labs/Lab07.1-full-assignment.md", "Lab 7 spec")],
    "Ch 18: Consuming Data": [("LA's/LA18.1-full-assignment.md", "LA18.1 spec")],
    "Ch 19: Designing APIs": [("LA's/LA19.1-full-assignment.md", "LA19.1 spec")],
    "Ch 20: Code Quality and Refactoring": [("LA's/LA20.1-full-assignment.md", "LA20.1 spec"), ("Labs/Lab07.1-full-assignment.md", "Lab 7 spec")],
    "Ch 21: Debugging": [("LA's/LA21.1-full-assignment.md", "LA21.1 spec"), ("Labs/Lab07.1-full-assignment.md", "Lab 7 spec")],
    "Ch 22: Adding New Features": [("LA's/LA22.1-full-assignment.md", "LA22.1 spec"), ("Labs/Lab08.1-full-assignment.md", "Lab 8 spec")],
}

# Part 1 duplicate groups (same exercise written 2-3 times). The card with the longest back is
# kept; the rest are suspended, never deleted, and never if they have review history.
DUP_GROUPS: list[list[str]] = [
    ["3fa23dc715964665b706440f0863ae51", "c337c00d9e074a1483f94325db398bd9"],                       # freezingHourNumbers
    ["8b9b85c56b344db081a8b960bc36df10", "4b093932cee24d18996c7fb9883c6a0c"],                       # peakHumidity
    ["0e6f7423c3044856ac979045b026ad1e", "f6d2aae6a44947ddae8e994575213165", "424928566ef24946bf9c17555aa05a4a"],  # peakHumidityWhenFreezing
    ["b93fdf50b2c34ab290a91515d2912abf", "20f3690dbc5d4e5d9050f37935ee820b"],                       # firstComfortable
    ["5418243ffd1142ca8ab144af581c9cce", "b4abb742ddd142259505dec546f7ceaa"],                       # muggyHours
    ["5e20dd976ea648ad9844afdf173c0e69", "3e64b1ffe9ea4892992a40dc626011da", "2ec79021b36e49618a4d9f047b6078e2"],  # comfort model
    ["e8baa5ceba084e9ea27bf3d08591fcb3", "c9eee2e6ad954209809f7d72172536f7", "e4e7c84558ea439fbd6d34a2daf6712d"],  # hasCloseTemperatures
    ["b3da9d74187a465c9184a64c0a993d69", "949976464d5a4ec99af0568187ca4534"],                       # BankAccount (LA03)
    ["2601f979549b44f29b356aea48cbdd45", "be7ec97787544242ab64869efe6aac80", "94766e96322a4d5eb8a8a1155dad6a3d"],  # setTaskStatus
    ["612207166e0d4f96b4e9a675e82d8dc5", "b0809e7b18ad42f1b2f1a92ca5914bc0"],                       # diffHoursWorked
    ["92a4703318ce4120880ac048dfec6a00", "a515f22947b149dea048294f0b7ac0e6"],                       # invariant: two things
    ["f0b3f9e66f1b4e27b667b0dbc1e684a6", "a3cf0f868fee40eca607238784063077"],                       # tests failed on a correct solution
    ["150fe255410b4007bbd5061ee2da59c0", "abcf9284d9874a29bb9ff02ec158344c"],                       # Reid's order of work
    ["3b8917787e404c5e9acdfb4dee361a52", "fc59e7e45de94029bcec7ecfed35155d"],                       # ECs come from the spec
    ["efa4a1e3f7d44264af5c935615b1c82b", "cb8341d71f87438fb50129d87fa9bf59"],                       # array-input classes
]
STAY_IN_PART1_TAGS = {"mt2-logistics", "mt2-strategy"}  # exam-strategy cards keep living in the Part 1 deck


# ── helpers ──────────────────────────────────────────────────────────────────

def bare(name: str) -> str:
    return name.removeprefix("! ")


async def find_deck(db, user, name: str) -> Deck | None:
    return await db.scalar(
        select(Deck).where(Deck.user_id == user.id, Deck.name.in_([name, "! " + name]))
    )


async def ensure_deck(db, user, name: str, parent: Deck, **fields) -> Deck:
    deck = await find_deck(db, user, name)
    if deck is None:
        deck = Deck(user_id=user.id, name=name, parent_id=parent.id, default_priority=50,
                    source_documents=[], **fields)
        db.add(deck)
        await db.flush()
        log.info(f"  + created deck '{name}'")
    return deck


def missing_block(docs_dir: Path, needs: list[tuple[str, str]], header: str) -> tuple[str, int]:
    lines, missing = [], 0
    for rel, label in needs:
        if not (docs_dir / rel).exists():
            lines.append(f"  • [needs: {rel}] {label}")
            missing += 1
    if not missing:
        return "", 0
    return f"{MISSING_MARK}{header}\nMissing for full coverage:\n" + "\n".join(lines), missing


def with_block(base: str, block: str) -> str:
    base = (base or "").split("\n\n" + MISSING_MARK)[0].split(MISSING_MARK)[0].rstrip()
    return base + ("\n\n" + block if block else "")


def set_bang(deck: Deck, missing: bool) -> None:
    name = bare(deck.name)
    deck.name = ("! " + name) if missing else name


async def counts(db, deck: Deck) -> tuple[int, int]:
    total = await db.scalar(select(func.count()).select_from(Card).where(Card.deck_id == deck.id))
    susp = await db.scalar(select(func.count()).select_from(Card).where(Card.deck_id == deck.id, Card.suspended.is_(True)))
    return total or 0, susp or 0


async def snapshot(db, user) -> dict[str, tuple[int, int, str]]:
    decks = (await db.scalars(select(Deck).where(Deck.user_id == user.id))).all()
    by_id = {d.id: d for d in decks}
    out = {}
    for d in decks:
        t, s = await counts(db, d)
        parent = bare(by_id[d.parent_id].name) if d.parent_id in by_id else "-"
        out[bare(d.name)] = (t, s, parent, d.name)
    return out


# ── steps ────────────────────────────────────────────────────────────────────

async def build_structure(db, user, root: Deck, part1: Deck, part2: Deck) -> tuple[Deck, Deck, dict[int, Deck]]:
    mt3 = await ensure_deck(db, user, MT3_NAME, root)
    mt3.parent_id = root.id
    mt3.default_priority = MT3_PRIORITY
    mt3.target_event_title = MT3_TITLE
    mt3.target_event_date = MT3_DATE
    mt3.thematic_nature = "Everything Midterm 3 tests: Ch 08–16 plus the Part 1 skills it builds on."
    carry = await ensure_deck(db, user, CARRY_NAME, mt3)
    carry.parent_id = mt3.id
    carry.default_priority = MT3_PRIORITY
    carry.target_event_title = MT3_TITLE
    carry.target_event_date = MT3_DATE
    carry.thematic_nature = "Part 1 cards MT3 still depends on (copies; originals stay in Part 1)."
    carry.documentation = ("Copies of Part 1 cards MT3 depends on: exam mechanics and grading, the "
                           "ECP/BVA checklist, assert vs Result, toolkit testing habits, aliasing and "
                           "defensive copies, async testing. Each copy is tagged copy-of:<original id>.")

    chapters: dict[int, Deck] = {}
    for num, ch in CHAPTERS.items():
        deck = await find_deck(db, user, ch["name"])
        if deck is None:
            raise SystemExit(f"Chapter deck not found: {ch['name']}")
        deck.parent_id = mt3.id
        deck.target_event_title = MT3_TITLE
        deck.target_event_date = MT3_DATE
        deck.default_priority = MT3_PRIORITY
        deck.thematic_nature = ch["theme"]
        chapters[num] = deck
    return mt3, carry, chapters


async def refresh_docs(db, user, docs_dir: Path, mt3: Deck | None, chapters: dict[int, Deck], part2: Deck, part3: Deck | None) -> None:
    any_missing = False
    for num, ch in CHAPTERS.items():
        deck = chapters[num]
        header = (f"Partial coverage — built from the textbook only (pp. {ch['pages']})."
                  if num >= 10 else f"Partial coverage (pp. {ch['pages']}).")
        block, missing = missing_block(docs_dir, ch["needs"], header)
        deck.documentation = with_block(ch["doc"], block)
        set_bang(deck, missing > 0)
        any_missing |= missing > 0
    if mt3 is not None:
        scope = ("Midterm 3 (15%), Fri Nov 13, in class, coding on your own laptop. Scope assumed to be "
                 "Ch 08–16 (L08–L16): MT2 covered L01–L07 and excluded L08/L09 (Piazza @313). Confirm on "
                 "Piazza/ELMS.")
        block = (f"{MISSING_MARK}Some chapters are built from the textbook only; see the chapter decks "
                 "marked '!'.\nMissing for full coverage:\n  • [needs: see chapters] LA/Lab specs for Ch 10–16"
                 if any_missing else "")
        mt3.documentation = with_block(scope, block)
        set_bang(mt3, any_missing)
    # Part 2 is an empty placeholder while its chapters live under Midterm 3.
    p2_block = (f"{MISSING_MARK}Placeholder while Ch 10–16 live under '{MT3_NAME}'.\nMissing for full coverage:\n"
                "  • [needs: LA's/LA10-LA16] LA10–LA16 specs") if any_missing else ""
    part2.documentation = with_block(
        "Chapters 10 to 16. Scope for Midterm 3 (Nov 13) and the Final. While MT3 is pending, the "
        f"chapter decks live under '{MT3_NAME}'; run build_mt3_decks.py --revert-structure afterwards.", p2_block)
    set_bang(part2, any_missing)
    if part3 is not None:
        p3_missing = False
        for name, needs in PART3_NEEDS.items():
            deck = await find_deck(db, user, name)
            if deck is None:
                continue
            block, missing = missing_block(docs_dir, needs, "No cards yet — textbook available, specs not released.")
            deck.documentation = with_block(deck.documentation or "", block)
            set_bang(deck, missing > 0)
            p3_missing |= missing > 0
        p3_block = (f"{MISSING_MARK}Chapters 17–22 have no cards yet.\nMissing for full coverage:\n"
                    "  • [needs: LA's/LA17-LA22] LA17–LA22 specs") if p3_missing else ""
        part3.documentation = with_block(part3.documentation or "", p3_block)
        set_bang(part3, p3_missing)


async def replace_old_ch8_ch9(db, chapters: dict[int, Deck]) -> int:
    """Delete never-reviewed pre-MT3 Ch 08/09 notes; suspend any that have history."""
    removed = 0
    for num in (8, 9):
        cards = (await db.scalars(select(Card).where(Card.deck_id == chapters[num].id))).all()
        old = [c for c in cards if "mt3" not in (c.tags or [])]
        to_delete = []
        for c in old:
            logs = await db.scalar(select(func.count()).select_from(ReviewLog).where(ReviewLog.card_id == c.id))
            if c.state == "new" and not logs:
                to_delete.append(c.note_id)
            else:
                c.suspended = True
        if to_delete:
            await db.execute(delete(Note).where(Note.id.in_(to_delete)))  # cascades to cards/references
            removed += len(to_delete)
    await db.flush()
    return removed


async def ingest_mt3_json(db, user, mt3_dir: Path, chapters: dict[int, Deck], carry: Deck, only: int | None) -> None:
    for path in sorted(mt3_dir.glob("cpsc210_mt3_*.json")):
        m = re.match(r"cpsc210_mt3_ch(\d+)_", path.name)
        if m:
            num = int(m.group(1))
            if num not in chapters or (only is not None and num != only):
                continue
            deck = chapters[num]
        elif "carry_forward" in path.name:
            if only is not None:
                continue
            deck = carry
        else:
            continue
        items = json.loads(path.read_text(encoding="utf-8"))
        res = await ingest_notes_list(db, user, items, deck, path.name,
                                      default_priority=MT3_PRIORITY, extra_tags=["mt3"],
                                      seen_fronts=await subtree_fronts(db, user, deck)
                                      | await coding_fronts(db, user)
                                      | await la_lab_fronts(db, user))
        log.info(f"  {bare(deck.name)}: +{res.cards} cards from {path.name} ({res.skipped} already present)")


async def subtree_ids(db, user, deck: Deck) -> list:
    decks = (await db.scalars(select(Deck).where(Deck.user_id == user.id))).all()
    kids: dict = {}
    for d in decks:
        kids.setdefault(d.parent_id, []).append(d.id)
    out, stack = [], [deck.id]
    while stack:
        cur = stack.pop()
        out.append(cur)
        stack.extend(kids.get(cur, []))
    return out


async def subtree_fronts(db, user, deck: Deck) -> set[str]:
    ids = await subtree_ids(db, user, deck)
    rows = await db.execute(
        select(Note.field_values).join(Card, Card.note_id == Note.id).where(Card.deck_id.in_(ids))
    )
    return {str((fv or {}).get("Front", "")).strip() for (fv,) in rows.all()}


async def coding_deck(db, user, create: bool = False) -> Deck | None:
    mt3 = await find_deck(db, user, MT3_NAME)
    if mt3 is None:
        return None
    deck = await db.scalar(select(Deck).where(Deck.user_id == user.id, Deck.parent_id == mt3.id,
                                              Deck.name == CODING_NAME))
    if deck is None and create:
        deck = Deck(user_id=user.id, parent_id=mt3.id, name=CODING_NAME, source_documents=[])
        db.add(deck)
        await db.flush()
        log.info(f"  + created deck '{CODING_NAME}'")
    if deck is not None and create:
        deck.position = -1  # top of Midterm 3
        deck.default_priority = CODING_PRIORITY
        deck.target_event_title = MT3_TITLE
        deck.target_event_date = MT3_DATE
        deck.thematic_nature = "Coding only: implement-from-spec and write-the-tests cards for MT3."
        deck.documentation = ("Every MT3 card that makes you write code or tests, one subdeck per chapter. "
                              "Type the solution (or the chai tests) before revealing the answer; code cards "
                              "can be run against their test cases.")
    return deck


async def coding_fronts(db, user) -> set[str]:
    deck = await coding_deck(db, user)
    return await subtree_fronts(db, user, deck) if deck is not None else set()


async def la_lab_fronts(db, user) -> set[str]:
    """Fronts in the "Lecture Activities" and "Labs" decks (build_la_lab_decks.py moves LA08/LA09
    cards there), so re-ingesting the MT3 JSON never re-creates a card that was moved out."""
    root = await find_deck(db, user, ROOT_NAME)
    if root is None:
        return set()
    out: set[str] = set()
    for name in ("Lecture Activities", "Labs"):
        deck = await db.scalar(select(Deck).where(Deck.user_id == user.id, Deck.parent_id == root.id,
                                                  Deck.name == name))
        if deck is not None:
            out |= await subtree_fronts(db, user, deck)
    return out


def _is_practice(card: Card) -> bool:
    tags = set(card.tags or [])
    return "code" in tags or "test-writing" in tags


def _short(deck: Deck) -> str:
    name = bare(deck.name)
    return name.split(":")[0] if name.startswith("Ch ") else "Carry-forward"


async def apply_tiers(db, user, mt3_dir: Path, chapters: dict[int, Deck], carry: Deck, only: int | None) -> dict:
    """Create P1/P2/P3 subdecks in each MT3 chapter and move every MT3 card into its tier."""
    moved: dict = {}
    coding = await coding_deck(db, user, create=True)
    for path in sorted(mt3_dir.glob("cpsc210_mt3_*.json")):
        m = re.match(r"cpsc210_mt3_ch(\d+)_", path.name)
        if m:
            num = int(m.group(1))
            if num not in chapters or (only is not None and num != only):
                continue
            parent = chapters[num]
            order = num
        elif "carry_forward" in path.name and only is None:
            parent = carry
            order = 0
        else:
            continue
        code_name = f"Code · {_short(parent)}"
        code_sub = await db.scalar(select(Deck).where(Deck.user_id == user.id, Deck.parent_id == coding.id,
                                                      Deck.name == code_name))
        if code_sub is None:
            code_sub = Deck(user_id=user.id, parent_id=coding.id, name=code_name, source_documents=[])
            db.add(code_sub)
            await db.flush()
        code_sub.position = order
        code_sub.default_priority = CODING_PRIORITY
        code_sub.target_event_title = MT3_TITLE
        code_sub.target_event_date = MT3_DATE
        code_sub.thematic_nature = parent.thematic_nature
        code_sub.documentation = f"Coding and test-writing cards for {bare(parent.name)}."
        tier_of = {item["front"].strip(): item.get("tier", 2)
                   for item in json.loads(path.read_text(encoding="utf-8"))}
        subdecks: dict[int, Deck] = {}
        for t, (label, prio) in TIERS.items():
            sub = await db.scalar(select(Deck).where(Deck.user_id == user.id, Deck.parent_id == parent.id,
                                                     Deck.name == f"{_short(parent)} · {label}"))
            if sub is None:
                sub = Deck(user_id=user.id, parent_id=parent.id, name=f"{_short(parent)} · {label}",
                           source_documents=[], default_priority=prio)
                db.add(sub)
                await db.flush()
            sub.default_priority = prio
            sub.position = t
            sub.target_event_title = MT3_TITLE
            sub.target_event_date = MT3_DATE
            sub.thematic_nature = parent.thematic_nature
            sub.documentation = {1: "Code, test-writing and core-mechanism cards: what a LA-style coding exam "
                                    "graded on correctness and test-suite strength is most likely to need.",
                                 2: "Concepts that explain the P1 material and the design decisions behind it.",
                                 3: "Background, terminology and history; study only if time allows."}[t]
            subdecks[t] = sub
        ids = await subtree_ids(db, user, parent) + [code_sub.id]
        cards = (await db.scalars(select(Card).where(Card.deck_id.in_(ids)))).all()
        for c in cards:
            if "mt3" not in (c.tags or []):
                continue
            t = tier_of.get(str((c.note.field_values or {}).get("Front", "")).strip())
            if t is None:
                continue
            if _is_practice(c):
                c.deck_id = code_sub.id
                c.priority = CODING_PRIORITY
                moved["code"] = moved.get("code", 0) + 1
                continue
            c.deck_id = subdecks[t].id
            c.priority = TIERS[t][1]
            moved[t] = moved.get(t, 0) + 1
    await db.flush()
    return moved


def _route(card: Card) -> int | str | None:
    tags = set(card.tags or [])
    if tags & STAY_IN_PART1_TAGS:
        return "stay"
    doc = card.documentation or ""
    m = re.search(r"Textbook Ch\.? ?(\d)\b", doc) or re.search(r"LA0(\d)", doc)
    if m:
        return int(m.group(1))
    for t in tags:
        m = re.fullmatch(r"ch0?(\d)", t)
        if m:
            return int(m.group(1))
    if tags & {"async", "promises"}:
        return 7
    if tags & {"mutation", "aliasing"}:
        return 6
    if "recursion" in tags:
        return 2
    if "invariants" in tags:
        return 4
    return 3


async def cleanup_part1(db, user, part1: Deck) -> tuple[int, int]:
    ch_decks = {}
    for d in (await db.scalars(select(Deck).where(Deck.user_id == user.id, Deck.parent_id == part1.id))).all():
        m = re.match(r"Ch 0(\d):", bare(d.name))
        if m:
            ch_decks[int(m.group(1))] = d
    moved = 0
    for c in (await db.scalars(select(Card).where(Card.deck_id == part1.id))).all():
        dest = _route(c)
        if isinstance(dest, int) and dest in ch_decks:
            c.deck_id = ch_decks[dest].id
            moved += 1

    suspended = 0
    for group in DUP_GROUPS:
        cards = [c for c in [await db.get(Card, _uuid(cid)) for cid in group] if c is not None]
        if len(cards) < 2:
            continue
        cards.sort(key=lambda c: len(str((c.note.field_values or {}).get("Back", ""))), reverse=True)
        for c in cards[1:]:
            if c.state == "new" and not c.suspended:
                c.suspended = True
                suspended += 1
    await db.flush()
    return moved, suspended


def _uuid(hex_id: str):
    import uuid
    return uuid.UUID(hex_id)


async def revert_structure(db, user) -> None:
    part1 = await find_deck(db, user, PART1)
    part2 = await find_deck(db, user, PART2)
    root = await find_deck(db, user, ROOT_NAME)
    for num, ch in CHAPTERS.items():
        deck = await find_deck(db, user, ch["name"])
        if deck is None:
            continue
        deck.parent_id = (part1 if num <= 9 else part2).id
        deck.target_event_title = root.target_event_title
        deck.target_event_date = root.target_event_date
        deck.default_priority = 50
    log.info("Chapters moved back under Part 1 / Part 2 and retargeted to the Final. "
             f"'{MT3_NAME}' keeps only the carry-forward copies; suspend or delete it in the app.")


# ── main ─────────────────────────────────────────────────────────────────────

async def main(args) -> None:
    cards_root = Path(args.cards_root)
    mt3_dir = cards_root / "Cards" / "5 - MT3"
    docs_dir = cards_root / "Cards Documents"
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == args.email))
        if user is None:
            raise SystemExit(f"user {args.email} not found")
        before = await snapshot(db, user)

        if args.revert_structure:
            await revert_structure(db, user)
        else:
            root = await find_deck(db, user, ROOT_NAME)
            part1 = await find_deck(db, user, PART1)
            part2 = await find_deck(db, user, PART2)
            part3 = await find_deck(db, user, PART3)
            if not (root and part1 and part2):
                raise SystemExit("CPSC 210 root/Part decks not found; run populate_cpsc210.py first")

            mt3, carry, chapters = await build_structure(db, user, root, part1, part2)
            if not args.refresh_docs:
                if args.chapter is None:
                    n = await replace_old_ch8_ch9(db, chapters)
                    log.info(f"Removed {n} never-reviewed pre-MT3 Ch 08/09 notes")
                await ingest_mt3_json(db, user, mt3_dir, chapters, carry, args.chapter)
                tiers = await apply_tiers(db, user, mt3_dir, chapters, carry, args.chapter)
                log.info("Tiers: " + ", ".join(f"{'P' + str(t) if t != 'code' else 'Coding drills'}={n}"
                                               for t, n in sorted(tiers.items(), key=str)))
                if args.chapter is None:
                    moved, suspended = await cleanup_part1(db, user, part1)
                    log.info(f"Part 1 cleanup: moved {moved} cards into chapter decks, suspended {suspended} duplicates")
            await refresh_docs(db, user, docs_dir, mt3, chapters, part2, part3)

        await db.flush()
        after = await snapshot(db, user)
        log.info("\n%-44s %-10s %-10s %s" % ("deck", "before", "after", "parent (after)"))
        for name in sorted(set(before) | set(after)):
            b = before.get(name, (0, 0, "-", ""))
            a = after.get(name, (0, 0, "-", ""))
            if name.startswith("Default"):
                continue
            log.info("%-44s %-10s %-10s %s" % (a[3] or name, f"{b[0]}/{b[1]}s", f"{a[0]}/{a[1]}s", a[2]))
        log.info("(counts are total/suspended)")

        if args.dry_run:
            await db.rollback()
            log.info("\nDRY RUN — nothing was written.")
        else:
            await db.commit()
            log.info("\nCommitted.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true", help="show the before/after counts, write nothing")
    p.add_argument("--refresh-docs", action="store_true", help="only recompute the missing-docs blocks and '!' names")
    p.add_argument("--revert-structure", action="store_true", help="after MT3: move chapters back under the Parts")
    p.add_argument("--chapter", type=int, help="only ingest the 5 - MT3 JSON for this chapter")
    p.add_argument("--email", default=USER_EMAIL)
    p.add_argument("--cards-root", default=str(CARDS_ROOT), help="folder holding 'Cards' and 'Cards Documents'")
    asyncio.run(main(p.parse_args()))
