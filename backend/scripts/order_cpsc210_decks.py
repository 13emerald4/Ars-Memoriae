"""Reorder CPSC 210 decks to display in study order.

This script updates ONLY the `position` column of decks belonging to the user
michael.r.polley@outlook.com. It preserves cards, priorities, names, target dates,
and parent relationships.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from sqlalchemy import select, update  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import Deck, KnowledgeNode, User  # noqa: E402

TARGET_USER_EMAIL = "michael.r.polley@outlook.com"


def normalize_name(s: str) -> str:
    """Normalize deck names for matching, treating '! <name>' and '<name>' identically,
    and normalizing dashes/spaces."""
    s = s.strip()
    if s.startswith("!"):
        s = s[1:].strip()
    # Normalize em dash, en dash, and bullet
    s = s.replace("\u2014", "-").replace("\u2013", "-").replace("\u00b7", "-")
    return " ".join(s.split()).lower()



# Definition of expected structure:
# parent_norm_name -> list of (child_norm_name, expected_position)
HIERARCHY_ORDER = {
    # Children of Root "CPSC 210 — every function has a contract"
    "cpsc 210 - every function has a contract": [
        ("midterm 3 - nov 13", 0),
        ("part 1: foundations - keep the contract", 1),
        ("part 2: abstraction - hide behind the contract", 2),
        ("part 3: evolution - keep contracts stable", 3),
    ],
    # Children of "Midterm 3 — Nov 13"
    "midterm 3 - nov 13": [
        ("mt3 - carry-forward (copies)", 0),
        ("ch 08: designing for failure", 1),
        ("ch 09: validating behaviour", 2),
        ("ch 10: building abstractions", 3),
        ("ch 11: decomposing systems", 4),
        ("ch 12: encapsulating what varies", 5),
        ("ch 13: implementation freedom", 6),
        ("ch 14: defining boundaries", 7),
        ("ch 15: extending behaviour", 8),
        ("ch 16: growing systems", 9),
    ],
    # Children of "Part 1: Foundations — keep the contract"
    "part 1: foundations - keep the contract": [
        ("ch 01: learning a new language", 1),
        ("ch 02: modelling with types", 2),
        ("ch 03: checking invariants", 3),
        ("ch 04: maintaining invariants", 4),
        ("ch 05: arrays and iteration", 5),
        ("ch 06: mutation and side effects", 6),
        ("ch 07: asynchronous effects", 7),
    ],
    # Children of "Part 3: Evolution — keep contracts stable"
    "part 3: evolution - keep contracts stable": [
        ("ch 17: coupling", 1),
        ("ch 18: consuming data", 2),
        ("ch 19: designing apis", 3),
        ("ch 20: code quality and refactoring", 4),
        ("ch 21: debugging", 5),
        ("ch 22: adding new features", 6),
    ],
}


async def reorder_decks() -> None:
    async with SessionLocal() as db:
        # 1. Fetch user
        stmt_user = select(User).where(User.email == TARGET_USER_EMAIL)
        user = (await db.execute(stmt_user)).scalar_one_or_none()
        if not user:
            print(f"[ERROR] User {TARGET_USER_EMAIL} not found!")
            return

        print(f"Loaded user {user.email} (ID: {user.id})")

        # 2. Fetch all decks for user
        stmt_decks = select(Deck).where(Deck.user_id == user.id)
        decks = (await db.execute(stmt_decks)).scalars().all()
        print(f"Total decks found for user: {len(decks)}")

        # Check knowledge nodes with deck_id
        kn_count = (
            await db.execute(
                select(KnowledgeNode.id).where(
                    KnowledgeNode.user_id == user.id, KnowledgeNode.deck_id.is_not(None)
                )
            )
        ).all()
        has_knowledge_nodes = len(kn_count) > 0
        print(f"Linked KnowledgeNodes with deck_id: {len(kn_count)}")

        # Build lookups
        children_by_parent: dict[object, list[Deck]] = {}
        for d in decks:
            children_by_parent.setdefault(d.parent_id, []).append(d)

        # Locate root CPSC 210 deck (parent_id is None)
        root_deck = next(
            (d for d in decks if d.parent_id is None and "cpsc 210" in normalize_name(d.name)),
            None,
        )
        if not root_deck:
            print("[ERROR] Root CPSC 210 deck not found!")
            return

        print(f"Found root deck: {root_deck.name!r} (ID: {root_deck.id})")

        # Map normalized parent name -> Deck object
        parent_decks_by_norm: dict[str, Deck] = {
            normalize_name(root_deck.name): root_deck,
        }

        changes_count = 0
        unchanged_count = 0

        # Helper to process child list under a parent deck
        def process_parent(parent_deck: Deck, target_children: list[tuple[str, int]]) -> None:
            nonlocal changes_count, unchanged_count
            p_children = children_by_parent.get(parent_deck.id, [])
            norm_to_child = {normalize_name(c.name): c for c in p_children}

            for child_norm, expected_pos in target_children:
                child_deck = norm_to_child.get(child_norm)
                if not child_deck:
                    print(
                        f"[WARNING] Child deck '{child_norm}' not found under parent '{parent_deck.name}'"
                    )
                    continue

                # Record parent for subsequent levels if needed
                parent_decks_by_norm[child_norm] = child_deck

                if child_deck.position != expected_pos:
                    old_pos = child_deck.position
                    child_deck.position = expected_pos
                    print(
                        f"  [CHANGE] '{child_deck.name}': position {old_pos} -> {expected_pos} (Parent: '{parent_deck.name}')"
                    )
                    changes_count += 1
                else:
                    print(
                        f"  [OK] '{child_deck.name}': position {expected_pos} (already set, Parent: '{parent_deck.name}')"
                    )
                    unchanged_count += 1

                # If this child is one of the 10 Midterm 3 decks or Carry-forward, verify its tier subdecks
                sub_children = children_by_parent.get(child_deck.id, [])
                for sub in sub_children:
                    sub_norm = normalize_name(sub.name)
                    tier_pos = None
                    if "p1" in sub_norm:
                        tier_pos = 1
                    elif "p2" in sub_norm:
                        tier_pos = 2
                    elif "p3" in sub_norm:
                        tier_pos = 3

                    if tier_pos is not None:
                        if sub.position != tier_pos:
                            old_sub_pos = sub.position
                            sub.position = tier_pos
                            print(
                                f"    [CHANGE] Tier subdeck '{sub.name}': position {old_sub_pos} -> {tier_pos} (Parent: '{child_deck.name}')"
                            )
                            changes_count += 1
                        else:
                            print(
                                f"    [OK] Tier subdeck '{sub.name}': position {tier_pos} (already set)"
                            )
                            unchanged_count += 1

        # 3. Apply ordering level by level
        # Level 1: Root children
        print("\n--- Reordering Root Children ---")
        process_parent(root_deck, HIERARCHY_ORDER["cpsc 210 - every function has a contract"])

        # Level 2: Midterm 3 children
        print("\n--- Reordering Midterm 3 Children ---")
        mt3_deck = parent_decks_by_norm.get("midterm 3 - nov 13")
        if mt3_deck:
            process_parent(mt3_deck, HIERARCHY_ORDER["midterm 3 - nov 13"])
        else:
            print("[WARNING] 'Midterm 3 — Nov 13' not found!")

        # Level 2: Part 1 children
        print("\n--- Reordering Part 1 Children ---")
        part1_deck = parent_decks_by_norm.get("part 1: foundations - keep the contract")
        if part1_deck:
            process_parent(part1_deck, HIERARCHY_ORDER["part 1: foundations - keep the contract"])
        else:
            print("[WARNING] 'Part 1: Foundations' not found!")

        # Level 2: Part 3 children
        print("\n--- Reordering Part 3 Children ---")
        part3_deck = parent_decks_by_norm.get("part 3: evolution - keep contracts stable")
        if part3_deck:
            process_parent(part3_deck, HIERARCHY_ORDER["part 3: evolution - keep contracts stable"])
        else:
            print("[WARNING] 'Part 3: Evolution' not found!")

        # If knowledge_nodes are linked to decks, sync their position
        if has_knowledge_nodes:
            print("\nSyncing linked KnowledgeNodes...")
            for d in decks:
                await db.execute(
                    update(KnowledgeNode)
                    .where(KnowledgeNode.user_id == user.id, KnowledgeNode.deck_id == d.id)
                    .values(position=d.position)
                )

        # 4. Commit changes
        await db.commit()
        print(f"\n[DONE] Successfully committed. Total changes: {changes_count}, Unchanged: {unchanged_count}")


if __name__ == "__main__":
    asyncio.run(reorder_decks())
