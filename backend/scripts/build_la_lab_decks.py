"""Build the "Lecture Activities" and "Labs" decks under the CPSC 210 root.

What it does (idempotent; safe to re-run):

1. Creates "Lecture Activities" (subdecks LA01–LA09) and "Labs" (subdecks Lab 1–4) under the
   CPSC 210 root, after "Midterm 3 — Nov 13" and before the Parts.
2. MOVES every card whose source locator cites a lecture activity (LA01–LA09) into its LA
   subdeck, wherever it lives in the CPSC 210 tree (Part 1 chapters, MT3 tiers, Coding drills).
   Suspended duplicates and the MT3 carry-forward copies (tag ``mt3-copy``) stay where they are.
   A card's own priority is kept.
3. Ingests the Lab card JSON (``Cards/6 - Labs/cpsc210_lab0N_*.json``) into the Lab subdecks,
   skipping any Front the user already has, and moves existing cards whose locator cites a Lab
   (and no LA) into the matching Lab subdeck.
4. LA08, LA09 and Lab 4 are MT3 material (Ch 08/09): those subdecks get the MT3 target date so
   Event Horizon keeps compressing their intervals toward Nov 13.

Usage (from the backend folder, backend stopped):
    .venv\\Scripts\\python.exe scripts\\build_la_lab_decks.py --dry-run
    .venv\\Scripts\\python.exe scripts\\build_la_lab_decks.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import Card, Deck, User  # noqa: E402
from scripts.build_mt3_decks import (  # noqa: E402
    CARDS_ROOT,
    MT3_DATE,
    MT3_TITLE,
    PART1,
    PART2,
    PART3,
    ROOT_NAME,
    USER_EMAIL,
    bare,
    find_deck,
    snapshot,
    subtree_ids,
)
from scripts.cpsc210_ingest import all_user_fronts, ingest_notes_list  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("build_la_lab")

LA_NAME = "Lecture Activities"
LABS_NAME = "Labs"
MT3_MAIN = "Midterm 3 — Nov 13"
# Root order: MT3 first, then the two cross-cutting decks, then the Parts.
ROOT_ORDER = [MT3_MAIN, LA_NAME, LABS_NAME, PART1, PART2, PART3]

LA_TOPICS = {
    1: "Ch 01 — Learning a New Language",
    2: "Ch 02 — Modelling With Types",
    3: "Ch 03 — Checking Invariants",
    4: "Ch 04 — Maintaining Invariants",
    5: "Ch 05 — Arrays and Iteration",
    6: "Ch 06 — Mutation and Side Effects",
    7: "Ch 07 — Asynchronous Effects",
    8: "Ch 08 — Designing for Failure",
    9: "Ch 09 — Validating Behaviour",
}
LAB_TITLES = {
    1: ("Lab 1 — Reading the Tides", "Ch 1–4: invariants, makeReading's Result, boundaries, rule of twelfths, recursion over List."),
    2: ("Lab 2 — Charting the Tides", "Ch 1–6: array operations, extremes, daily summaries, passage windows, the TideStation closure."),
    3: ("Lab 3 — Serving the Tides", "Ch 1–7: REST handlers, status codes 200/201/400/404/409, parseReading, the ?day filter, API.md."),
    4: ("Lab 4 — Keeping the Tides", "Ch 1–9: async persistence, loadStation through the same checks, 500s, windows and extremes endpoints."),
}
MT3_LAS = {8, 9}
MT3_LABS = {4}
MT3_SUB_PRIORITY = 90

LA_RE = re.compile(r"\bLA ?0?(\d)(?:\.\d)?\b")   # "LA06.1 — …", "LA01 Task 1"; case-sensitive so "Lab01" never matches
LAB_RE = re.compile(r"\bLab ?0?(\d)\b")          # "Lab 2 passageWindows", "Lab01.1 — …"


def locator_text(card: Card) -> str:
    parts = []
    for s in card.source_documents or []:
        if isinstance(s, dict):
            parts.append(str(s.get("locator", "")))
    m = re.search(r"\*\*Locator\*\*: (.*)", card.documentation or "")
    if m:
        parts.append(m.group(1))
    return " ".join(parts)


def classify(card: Card) -> tuple[str, int] | None:
    loc = locator_text(card)
    m = LA_RE.search(loc)
    if m and 1 <= int(m.group(1)) <= 9:
        return "la", int(m.group(1))
    m = LAB_RE.search(loc)
    if m and int(m.group(1)) in LAB_TITLES:
        return "lab", int(m.group(1))
    return None


async def child(db, user, parent: Deck, name: str) -> Deck | None:
    return await db.scalar(select(Deck).where(Deck.user_id == user.id, Deck.parent_id == parent.id,
                                              Deck.name.in_([name, "! " + name])))


async def ensure_child(db, user, parent: Deck, name: str) -> Deck:
    deck = await child(db, user, parent, name)
    if deck is None:
        deck = Deck(user_id=user.id, parent_id=parent.id, name=name, source_documents=[], default_priority=50)
        db.add(deck)
        await db.flush()
        log.info(f"  + created deck '{name}'")
    return deck


def mt3_dated(deck: Deck, on: bool) -> None:
    deck.target_event_title = MT3_TITLE if on else None
    deck.target_event_date = MT3_DATE if on else None


async def build_structure(db, user, root: Deck) -> tuple[Deck, dict[int, Deck], Deck, dict[int, Deck]]:
    la = await ensure_child(db, user, root, LA_NAME)
    la.thematic_nature = "Lecture activities: the PrairieLearn workspaces the midterms are modelled on."
    la.documentation = ("Every card drawn from a lecture activity (LA01–LA09), one subdeck per LA. "
                        "Midterms are LA-style workspaces graded on correctness and test-suite strength, so these "
                        "are the closest thing to past exam questions. LA08 and LA09 are MT3 scope and carry the "
                        "MT3 date.")
    la_subs: dict[int, Deck] = {}
    for n, topic in LA_TOPICS.items():
        sub = await ensure_child(db, user, la, f"LA{n:02d}")
        sub.position = n
        sub.thematic_nature = topic
        sub.documentation = f"Cards drawn from LA{n:02d}.1 ({topic})."
        mt3_dated(sub, n in MT3_LAS)
        if n in MT3_LAS:
            sub.default_priority = MT3_SUB_PRIORITY
        la_subs[n] = sub

    labs = await ensure_child(db, user, root, LABS_NAME)
    labs.thematic_nature = "Labs 1–4: the tide-station project, from one reading to a persistent REST service."
    labs.documentation = ("Cards built from the Lab01.1–Lab04.1 specs (Cards Documents\\Labs): implement-from-spec "
                          "code cards with runnable tests, write-the-tests cards (chai/vitest or the toolkit), and the "
                          "design decisions each lab grades. Lab 4 is MT3 scope (Ch 08) and carries the MT3 date.")
    lab_subs: dict[int, Deck] = {}
    for n, (name, theme) in LAB_TITLES.items():
        sub = await ensure_child(db, user, labs, name)
        sub.position = n
        sub.thematic_nature = theme
        sub.documentation = f"Cards built from Lab0{n}.1 ({name.split(' — ')[1]}). {theme}"
        mt3_dated(sub, n in MT3_LABS)
        sub.default_priority = MT3_SUB_PRIORITY if n in MT3_LABS else 60
        lab_subs[n] = sub

    # root order
    for pos, name in enumerate(ROOT_ORDER):
        d = await child(db, user, root, name)
        if d is not None:
            d.position = pos
    await db.flush()
    return la, la_subs, labs, lab_subs


async def move_cards(db, user, root: Deck, la_subs: dict[int, Deck], lab_subs: dict[int, Deck]) -> dict:
    ids = await subtree_ids(db, user, root)
    cards = (await db.scalars(select(Card).where(Card.deck_id.in_(ids)))).all()
    moved: dict = {}
    for c in cards:
        if c.suspended or "mt3-copy" in (c.tags or []):
            continue
        kind = classify(c)
        if kind is None:
            continue
        target = (la_subs if kind[0] == "la" else lab_subs)[kind[1]]
        if c.deck_id == target.id:
            continue
        c.deck_id = target.id
        key = f"LA{kind[1]:02d}" if kind[0] == "la" else f"Lab {kind[1]}"
        moved[key] = moved.get(key, 0) + 1
    await db.flush()
    return moved


async def ingest_labs(db, user, labs_dir: Path, lab_subs: dict[int, Deck]) -> None:
    if not labs_dir.exists():
        log.info(f"  (no lab card folder at {labs_dir})")
        return
    seen = await all_user_fronts(db, user)
    for path in sorted(labs_dir.glob("cpsc210_lab0*.json")):
        m = re.match(r"cpsc210_lab0(\d)_", path.name)
        if not m or int(m.group(1)) not in lab_subs:
            continue
        deck = lab_subs[int(m.group(1))]
        items = json.loads(path.read_text(encoding="utf-8"))
        res = await ingest_notes_list(db, user, items, deck, path.name, extra_tags=["lab"], seen_fronts=seen)
        log.info(f"  {deck.name}: +{res.cards} cards from {path.name} ({res.skipped} already present)")


async def main(args) -> None:
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == args.email))
        if user is None:
            raise SystemExit(f"no user {args.email}")
        root = await find_deck(db, user, ROOT_NAME)
        if root is None:
            raise SystemExit(f"no deck '{ROOT_NAME}'")
        before = await snapshot(db, user)

        log.info("== structure")
        _, la_subs, _, lab_subs = await build_structure(db, user, root)
        log.info("== ingest lab cards")
        await ingest_labs(db, user, Path(args.cards_root) / "Cards" / "6 - Labs", lab_subs)
        log.info("== move LA / Lab cards")
        moved = await move_cards(db, user, root, la_subs, lab_subs)
        for k in sorted(moved):
            log.info(f"  {k}: {moved[k]} moved")

        after = await snapshot(db, user)
        log.info("\n%-52s %8s %8s" % ("deck", "before", "after"))
        for name in sorted(set(before) | set(after)):
            b = before.get(name, (0, 0, "-", name))
            a = after.get(name, (0, 0, "-", name))
            if b[:2] != a[:2]:
                log.info("%-52s %4d/%-3d %4d/%-3d" % (name[:52], b[0], b[1], a[0], a[1]))
        if args.dry_run:
            await db.rollback()
            log.info("\n(dry run: rolled back)")
        else:
            await db.commit()
            log.info("\ncommitted")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--email", default=USER_EMAIL)
    p.add_argument("--cards-root", default=str(CARDS_ROOT))
    asyncio.run(main(p.parse_args()))
