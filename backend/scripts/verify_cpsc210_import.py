"""Verify CPSC 210 import in Ars Memoriae."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import httpx
from sqlalchemy import select

from app.core.security import create_access_token
from app.db import SessionLocal
from app.models import Card, CardReference, Deck, Note, User
from app.services.code_runner_service import run_code

USER_EMAIL = "michael.r.polley@outlook.com"

EXPECTED_COUNTS = {
    "LA01": 4,
    "LA02": 4,
    "LA03": 4,
    "LA04": 4,
    "LA05": 9,
    "LA06": 9,
    "LA07": 8,
    "Lab01 - Reading the Tides": 10,
    "Lab02 - Charting the Tides": 12,
    "Lab03 - Serving the Tides": 13,
    "Lab04 - Keeping the Tides": 12,
}


async def verify():
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == USER_EMAIL))
        assert user, "User not found"

        # 1. Deck Hierarchy
        root = await db.scalar(select(Deck).where(Deck.user_id == user.id, Deck.name == "CPSC 210", Deck.parent_id.is_(None)))
        assert root, "Root deck 'CPSC 210' not found"

        la_parent = await db.scalar(select(Deck).where(Deck.user_id == user.id, Deck.name == "Lecture Activities", Deck.parent_id == root.id))
        assert la_parent, "Sub-parent 'Lecture Activities' not found"

        labs_parent = await db.scalar(select(Deck).where(Deck.user_id == user.id, Deck.name == "Labs", Deck.parent_id == root.id))
        assert labs_parent, "Sub-parent 'Labs' not found"

        print("Deck hierarchy verified:")
        print(f"  Root: {root.name} (id={root.id})")
        print(f"    Sub-parent 1: {la_parent.name} (id={la_parent.id})")
        print(f"    Sub-parent 2: {labs_parent.name} (id={labs_parent.id})")

        # 2. Check counts and schema for each child deck
        total_cards_db = 0
        total_code_cards = 0
        total_qa_cards = 0
        total_citations = 0
        sample_code_cards = []

        print("\nChild Deck Counts & Schema Integrity:")
        for name, expected in EXPECTED_COUNTS.items():
            parent_id = la_parent.id if name.startswith("LA") else labs_parent.id
            deck = await db.scalar(select(Deck).where(Deck.user_id == user.id, Deck.name == name, Deck.parent_id == parent_id))
            assert deck, f"Deck {name} not found under parent {parent_id}"

            cards = (await db.scalars(select(Card).where(Card.deck_id == deck.id))).all()
            actual = len(cards)
            assert actual == expected, f"Count mismatch in {name}: got {actual}, expected {expected}"
            total_cards_db += actual

            for c in cards:
                note = await db.get(Note, c.note_id)
                fv = note.field_values or {}
                assert fv.get("Front") or fv.get("front"), f"Card {c.id} missing Front"
                assert fv.get("Back") or fv.get("back"), f"Card {c.id} missing Back"
                is_code = fv.get("card_type") == "code" or "code" in (c.tags or [])
                if is_code:
                    total_code_cards += 1
                    assert fv.get("starter_code"), f"Code card {c.id} missing starter_code"
                    assert fv.get("test_cases"), f"Code card {c.id} missing test_cases"
                    if len(sample_code_cards) < 2 and name in ("LA01", "Lab01 - Reading the Tides"):
                        sample_code_cards.append((name, fv.get("title") or fv.get("Front")[:40], fv.get("Back"), fv.get("test_cases"), fv.get("language", "typescript")))
                else:
                    total_qa_cards += 1

                # Citations
                refs = (await db.scalars(select(CardReference).where(CardReference.card_id == c.id))).all()
                total_citations += len(refs)

            print(f"  [PASS] {name}: {actual}/{expected} cards (code/qa verified)")

        print("\nTotals in DB:")
        print(f"  Total cards: {total_cards_db} (expected 89)")
        print(f"  Total code cards: {total_code_cards} (42 LA + 22 Lab = 64)")
        print(f"  Total QA cards: {total_qa_cards} (25 Lab QA = 25)")
        print(f"  Total citations created: {total_citations}")

        # 3. Live Server API Check
        token = create_access_token(user.id)
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            resp = await client.get("/api/decks", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200, f"API failed with {resp.status_code}"
            decks_api = resp.json()
            root_api = next((d for d in decks_api if d["name"] == "CPSC 210"), None)
            assert root_api, "Root deck 'CPSC 210' not found in GET /api/decks"
            print("\nLive API GET /api/decks check:")
            print(f"  Root deck 'CPSC 210' found with total_card_count = {root_api.get('total_card_count')}")

        # 4. Sandbox Test of Sample Cards
        print("\nTesting Sample Code Cards in Sandbox:")
        for deck_name, title, code, test_cases, lang in sample_code_cards:
            print(f"  Running card from {deck_name}: {title}...")
            res = await run_code(code=code, test_cases=test_cases, language=lang)
            status = res.get("status")
            passed = res.get("passed_count")
            total = res.get("total_count")
            print(f"    -> Result: {status} ({passed}/{total} passed, runtime {res.get('runtime_ms')}ms)")
            assert status == "Accepted", f"Sandbox run failed: {res}"

    print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(verify())
