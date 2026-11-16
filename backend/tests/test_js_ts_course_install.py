"""Installing the JavaScript & TypeScript course into a user's decks."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.content.js_ts_course import COURSE, ROOT_NAME, iter_cards
from app.content.js_ts_course.install import ReviewHistoryExists, install_course
from app.db import SessionLocal
from app.models import Card, CardReference, Deck, Note, ReviewLog, User
from app.services.note_service import default_note_type, sync_cards

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
HAS_TSC = (FRONTEND / "node_modules" / "typescript" / "package.json").exists()

TOTAL_CARDS = sum(1 for _ in iter_cards())
TOTAL_DECKS = sum(1 + len(p.subdecks) for p in COURSE)


async def _me(client) -> User:
    me = (await client.get("/api/me")).json()
    async with SessionLocal() as db:
        return await db.get(User, uuid.UUID(me["id"]))


async def _install(user_id, *, force: bool = False):
    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        report = await install_course(db, user, force=force)
        await db.commit()
        return report


async def _old_deck(user_id) -> tuple[uuid.UUID, uuid.UUID]:
    """An older version of the deck: the root, one subdeck, one card. Returns (root, card)."""
    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        root = Deck(user_id=user.id, name=ROOT_NAME)
        db.add(root)
        await db.flush()
        child = Deck(user_id=user.id, name="Part 1: old", parent_id=root.id)
        db.add(child)
        await db.flush()
        nt = await default_note_type(db, user, "basic")
        note = Note(
            user_id=user.id, note_type_id=nt.id, field_values={"Front": "old?", "Back": "old"}
        )
        db.add(note)
        await db.flush()
        (card,) = await sync_cards(db, note, nt, child.id)
        await db.commit()
        return root.id, card.id


async def _cards_under(root_id) -> list[Card]:
    async with SessionLocal() as db:
        ids, frontier = [root_id], [root_id]
        while frontier:
            frontier = (await db.scalars(select(Deck.id).where(Deck.parent_id.in_(frontier)))).all()
            ids.extend(frontier)
        return (await db.scalars(select(Card).where(Card.deck_id.in_(ids)))).all()


@pytest.mark.asyncio
async def test_install_creates_the_whole_course(auth_client):
    user = await _me(auth_client)
    report = await _install(user.id)
    assert report.root_created
    assert report.cards_created == TOTAL_CARDS
    assert report.decks_created == TOTAL_DECKS
    assert report.citations_created == sum(
        1 for *_, c in iter_cards() if c.source and c.source.quote
    )

    decks = (await auth_client.get("/api/decks")).json()
    root = next(d for d in decks if d["name"] == ROOT_NAME)
    cards = await _cards_under(uuid.UUID(root["id"]))
    assert len(cards) == TOTAL_CARDS
    assert all("js-ts-course" in c.tags for c in cards)

    async with SessionLocal() as db:
        refs = await db.scalar(
            select(func.count())
            .select_from(CardReference)
            .where(CardReference.card_id.in_([c.id for c in cards]))
        )
    assert refs == report.citations_created


@pytest.mark.asyncio
async def test_installed_code_cards_run_in_review(auth_client):
    user = await _me(auth_client)
    await _install(user.id)
    cards = (await auth_client.get("/api/cards", params={"tag": "js02-port-default"})).json()
    assert len(cards) == 1
    card_id = cards[0]["id"]

    good = "function getPort(config) {\n  return config.port ?? 3000;\n}\n"
    run = await auth_client.post(
        f"/api/review/{card_id}/run-code", json={"code": good, "language": "javascript"}
    )
    assert run.status_code == 200, run.text
    assert run.json()["status"] == "Accepted"

    buggy = "function getPort(config) {\n  return config.port || 3000;\n}\n"
    run = await auth_client.post(
        f"/api/review/{card_id}/run-code", json={"code": buggy, "language": "javascript"}
    )
    assert run.json()["status"] == "Wrong Answer"


@pytest.mark.asyncio
@pytest.mark.skipif(not HAS_TSC, reason="TypeScript not installed (npm ci in frontend/)")
async def test_installed_typescript_cards_are_type_checked(auth_client):
    user = await _me(auth_client)
    await _install(user.id)
    card_id = (await auth_client.get("/api/cards", params={"tag": "ts22-pluck"})).json()[0]["id"]

    loose = "function pluck(items: any[], key: string): any[] {\n  return items.map((item) => item[key]);\n}\n"
    run = await auth_client.post(
        f"/api/review/{card_id}/run-code", json={"code": loose, "language": "typescript"}
    )
    assert run.json()["status"] == "Type Error", run.json()


@pytest.mark.asyncio
async def test_install_replaces_an_older_version_and_keeps_the_root(auth_client):
    user = await _me(auth_client)
    root_id, old_card = await _old_deck(user.id)

    report = await _install(user.id)
    assert not report.root_created
    assert report.removed_cards == 1
    assert report.removed_decks == 1

    async with SessionLocal() as db:
        assert await db.get(Card, old_card) is None
        roots = (
            await db.scalars(select(Deck).where(Deck.user_id == user.id, Deck.name == ROOT_NAME))
        ).all()
    assert [r.id for r in roots] == [root_id]
    assert len(await _cards_under(root_id)) == TOTAL_CARDS

    # Running it again replaces the course with itself.
    again = await _install(user.id)
    assert again.removed_cards == TOTAL_CARDS
    assert len(await _cards_under(root_id)) == TOTAL_CARDS


@pytest.mark.asyncio
async def test_install_refuses_to_delete_review_history_unless_forced(auth_client):
    user = await _me(auth_client)
    _, old_card = await _old_deck(user.id)
    async with SessionLocal() as db:
        db.add(ReviewLog(card_id=old_card, final_grade="good"))
        await db.commit()

    with pytest.raises(ReviewHistoryExists):
        await _install(user.id)
    async with SessionLocal() as db:
        assert await db.get(Card, old_card) is not None

    report = await _install(user.id, force=True)
    assert report.removed_cards == 1
