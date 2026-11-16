"""Installs the course into a user's decks, replacing an older version of it.

The root deck ("JavaScript & TypeScript: Zero to Mastery") is kept, so its id,
position and anything pointing at it survive; everything under it — subdecks,
notes, cards — is replaced by the course. Replacing would throw away review
history, so it is refused when any card under the root has been reviewed,
unless the caller passes ``force=True``.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Card, CardReference, Deck, KnowledgeNode, Note, ReviewLog, User
from app.services import tree_service
from app.services.note_service import default_note_type, sync_cards

from . import COURSE, ROOT_NAME, ROOT_SUMMARY
from .model import CodeCard, Source, Subdeck
from .render import card_fields, card_tags


class ReviewHistoryExists(RuntimeError):
    """The existing deck has review history that replacing it would delete."""


@dataclass
class InstallReport:
    root_created: bool
    removed_decks: int
    removed_cards: int
    decks_created: int
    cards_created: int
    citations_created: int


def _source_document(source: Source) -> dict:
    doc = {"name": source.title, "locator": source.url, "path": source.url, "type": "documentation"}
    if source.quote:
        doc["quote"] = source.quote
    return doc


def _subdeck_documentation(subdeck: Subdeck) -> str:
    links = "\n".join(f"- {s.title}: {s.url}" for s in subdeck.sources)
    return f"{subdeck.summary}\n\nRead more:\n{links}"


async def _subtree(db: AsyncSession, user: User, root: Deck) -> list:
    """Ids of every deck below ``root`` (not including it)."""
    found: list = []
    frontier = [root.id]
    while frontier:
        children = (
            await db.scalars(
                select(Deck.id).where(Deck.user_id == user.id, Deck.parent_id.in_(frontier))
            )
        ).all()
        frontier = [c for c in children if c not in found]
        found.extend(frontier)
    return found


async def install_course(db: AsyncSession, user: User, *, force: bool = False) -> InstallReport:
    """Install (or replace) the course for ``user``. The caller commits."""
    root = await db.scalar(
        select(Deck).where(
            Deck.user_id == user.id, Deck.parent_id.is_(None), Deck.name == ROOT_NAME
        )
    )
    root_created = root is None
    removed_decks = removed_cards = 0

    if root is None:
        root = Deck(user_id=user.id, name=ROOT_NAME)
        db.add(root)
        await db.flush()
    else:
        old_decks = await _subtree(db, user, root)
        scope = [root.id, *old_decks]
        reviewed = await db.scalar(
            select(func.count())
            .select_from(ReviewLog)
            .join(Card, Card.id == ReviewLog.card_id)
            .where(Card.deck_id.in_(scope))
        )
        if reviewed and not force:
            raise ReviewHistoryExists(
                f"{reviewed} reviews exist for cards in '{ROOT_NAME}'; replacing the deck would "
                "delete them. Run again with --force to replace it anyway."
            )

        # Same order as the app's own deck delete (routers/decks.py).
        note_ids = (
            await db.scalars(select(Card.note_id).where(Card.deck_id.in_(scope)).distinct())
        ).all()
        removed_cards = (
            await db.scalar(select(func.count()).select_from(Card).where(Card.deck_id.in_(scope)))
        ) or 0
        for note in (await db.scalars(select(Note).where(Note.id.in_(note_ids)))).all():
            await db.delete(note)
        await db.execute(delete(Card).where(Card.deck_id.in_(scope)))
        if old_decks:
            await tree_service.detach_entity_node(db, KnowledgeNode.deck_id.in_(old_decks))
            await db.execute(delete(Deck).where(Deck.id.in_(old_decks)))
        removed_decks = len(old_decks)
        await db.flush()

    root.documentation = ROOT_SUMMARY
    root.thematic_nature = "Learn to code by writing code"
    root.source_documents = [
        _source_document(
            Source(
                "MDN — JavaScript Guide",
                "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide",
            )
        ),
        _source_document(
            Source(
                "The TypeScript Handbook", "https://www.typescriptlang.org/docs/handbook/intro.html"
            )
        ),
    ]

    basic = await default_note_type(db, user, "basic", grading_profile="short_answer")
    code = await default_note_type(db, user, "basic", grading_profile="math_code")

    decks_created = cards_created = citations = 0
    for part_index, part in enumerate(COURSE):
        part_deck = Deck(
            user_id=user.id,
            parent_id=root.id,
            name=part.name,
            position=part_index,
            documentation=part.summary,
            thematic_nature=part.name.split(" · ", 1)[-1],
        )
        db.add(part_deck)
        await db.flush()
        decks_created += 1

        for sub_index, subdeck in enumerate(part.subdecks):
            deck = Deck(
                user_id=user.id,
                parent_id=part_deck.id,
                name=subdeck.name,
                position=sub_index,
                documentation=_subdeck_documentation(subdeck),
                source_documents=[_source_document(s) for s in subdeck.sources],
            )
            db.add(deck)
            await db.flush()
            decks_created += 1

            for card_index, item in enumerate(subdeck.cards):
                note_type = code if isinstance(item, CodeCard) else basic
                note = Note(
                    user_id=user.id,
                    note_type_id=note_type.id,
                    field_values=card_fields(item, subdeck.name),
                )
                db.add(note)
                await db.flush()
                created = await sync_cards(db, note, note_type, deck.id, tags=card_tags(item))
                for card in created:
                    card.position = card_index
                    if item.source and item.source.quote:
                        db.add(
                            CardReference(
                                card_id=card.id,
                                quote=item.source.quote,
                                quote_verified=True,
                                locator=item.source.url[:200],
                                source_title=item.source.title,
                            )
                        )
                        citations += 1
                cards_created += len(created)

    await db.flush()
    return InstallReport(
        root_created=root_created,
        removed_decks=removed_decks,
        removed_cards=removed_cards,
        decks_created=decks_created,
        cards_created=cards_created,
        citations_created=citations,
    )
