"""Associative Networks & Spreading Activation Service (§Neuroscience).

Implements the Collins & Loftus spreading activation model and multi-relational
associative graphs over flashcards and concept nodes.
"""

from __future__ import annotations

import uuid
from collections import defaultdict, deque

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Card, ConceptEdge, Deck, SisterPair, User
from app.services.rendering import render


async def get_edges(
    db: AsyncSession, user: User, card_id: uuid.UUID | None = None
) -> list[ConceptEdge]:
    stmt = select(ConceptEdge).where(ConceptEdge.user_id == user.id)
    if card_id is not None:
        stmt = stmt.where(
            or_(
                ConceptEdge.source_card_id == card_id,
                ConceptEdge.target_card_id == card_id,
            )
        )
    return list((await db.scalars(stmt)).all())


async def create_edge(
    db: AsyncSession,
    user: User,
    source_card_id: uuid.UUID,
    target_card_id: uuid.UUID,
    relationship_type: str = "associative",
    weight: float = 1.0,
) -> ConceptEdge:
    if source_card_id == target_card_id:
        raise ValueError("Cannot create an edge from a card to itself")

    # Check if existing edge already exists
    existing = await db.scalar(
        select(ConceptEdge).where(
            ConceptEdge.user_id == user.id,
            ConceptEdge.source_card_id == source_card_id,
            ConceptEdge.target_card_id == target_card_id,
        )
    )
    if existing:
        existing.relationship_type = relationship_type
        existing.weight = weight
        await db.commit()
        await db.refresh(existing)
        return existing

    edge = ConceptEdge(
        user_id=user.id,
        source_card_id=source_card_id,
        target_card_id=target_card_id,
        relationship_type=relationship_type,
        weight=weight,
    )
    db.add(edge)
    await db.commit()
    await db.refresh(edge)
    return edge


async def delete_edge(db: AsyncSession, user: User, edge_id: uuid.UUID) -> bool:
    edge = await db.get(ConceptEdge, edge_id)
    if edge is None or edge.user_id != user.id:
        return False
    await db.delete(edge)
    await db.commit()
    return True


async def get_graph(
    db: AsyncSession, user: User, deck_id: uuid.UUID | None = None
) -> dict:
    """Returns the full associative network (nodes and edges) for the user."""
    card_stmt = (
        select(Card, Deck)
        .join(Deck, Deck.id == Card.deck_id)
        .where(Deck.user_id == user.id, Card.suspended.is_(False))
    )
    if deck_id is not None:
        card_stmt = card_stmt.where(Card.deck_id == deck_id)

    rows = (await db.execute(card_stmt)).all()
    if not rows:
        return {"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0}

    nodes = []
    card_ids = set()
    for card, deck in rows:
        card_ids.add(card.id)
        front, _ = render(
            card.note.note_type.template_kind,
            card.note.field_values or {},
            card.template_slot,
        )
        # Concise title from first 60 chars of front
        title = " ".join(front.split())[:60] if front else f"Card {str(card.id)[:8]}"
        nodes.append(
            {
                "id": str(card.id),
                "card_id": str(card.id),
                "title": title,
                "deck_id": str(deck.id),
                "deck_name": deck.name,
                "state": card.state,
                "is_schema_checkpoint": card.is_schema_checkpoint,
                "spatial_x": card.spatial_x,
                "spatial_y": card.spatial_y,
                "spatial_locus": card.spatial_locus,
                "activation": 0.0,
            }
        )

    edge_stmt = select(ConceptEdge).where(
        ConceptEdge.user_id == user.id,
        ConceptEdge.source_card_id.in_(card_ids),
        ConceptEdge.target_card_id.in_(card_ids),
    )
    raw_edges = (await db.scalars(edge_stmt)).all()

    edges = [
        {
            "id": str(e.id),
            "source": str(e.source_card_id),
            "target": str(e.target_card_id),
            "relationship_type": e.relationship_type,
            "weight": e.weight,
        }
        for e in raw_edges
    ]

    return {
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
    }


async def spreading_activation(
    db: AsyncSession,
    user: User,
    source_card_id: uuid.UUID,
    decay: float = 0.6,
    max_depth: int = 2,
) -> list[dict]:
    """Computes spreading activation energy traversing outward from source_card_id.

    A_j = sum(A_i * w_ij * decay^depth)
    Models hippocampal-neocortical semantic priming across association links.
    """
    edges = await get_edges(db, user)
    adj: dict[uuid.UUID, list[tuple[uuid.UUID, float, str]]] = defaultdict(list)
    for e in edges:
        adj[e.source_card_id].append((e.target_card_id, e.weight, e.relationship_type))
        # Bidirectional associative propagation with slight attenuation for reverse
        adj[e.target_card_id].append((e.source_card_id, e.weight * 0.8, e.relationship_type))

    activations: dict[uuid.UUID, float] = defaultdict(float)
    depths: dict[uuid.UUID, int] = {}
    relationships: dict[uuid.UUID, str] = {}

    # BFS queue: (node_id, current_energy, current_depth)
    queue: deque[tuple[uuid.UUID, float, int]] = deque([(source_card_id, 1.0, 0)])
    visited_depth: dict[uuid.UUID, int] = {source_card_id: 0}

    while queue:
        curr, energy, depth = queue.popleft()
        if depth >= max_depth:
            continue

        for neighbor, weight, rel_type in adj[curr]:
            spread_energy = energy * weight * decay
            if spread_energy < 0.05:
                continue

            activations[neighbor] += spread_energy
            if neighbor not in depths or depths[neighbor] > depth + 1:
                depths[neighbor] = depth + 1
                relationships[neighbor] = rel_type

            if neighbor not in visited_depth or visited_depth[neighbor] > depth + 1:
                visited_depth[neighbor] = depth + 1
                queue.append((neighbor, spread_energy, depth + 1))

    # Remove source itself from activated neighbors
    activations.pop(source_card_id, None)
    if not activations:
        return []

    # Fetch card and deck titles
    target_ids = list(activations.keys())
    # Scoped to the caller's decks: an edge row is only a pair of ids, so a
    # stale or hostile one must not be able to pull in another account's card.
    cards = (
        await db.scalars(
            select(Card)
            .join(Deck, Card.deck_id == Deck.id)
            .where(
                Card.id.in_(target_ids),
                Card.suspended.is_(False),
                Deck.user_id == user.id,
            )
        )
    ).all()

    results = []
    for c in cards:
        front, _ = render(
            c.note.note_type.template_kind,
            c.note.field_values or {},
            c.template_slot,
        )
        title = " ".join(front.split())[:60] if front else f"Card {str(c.id)[:8]}"
        results.append(
            {
                "card_id": str(c.id),
                "title": title,
                "deck_name": c.deck.name if c.deck else "Default",
                "activation": round(activations[c.id], 3),
                "path_depth": depths.get(c.id, 1),
                "relationship_to_source": relationships.get(c.id, "associative"),
            }
        )

    results.sort(key=lambda r: r["activation"], reverse=True)
    return results


async def auto_discover_edges(db: AsyncSession, user: User) -> list[ConceptEdge]:
    """Auto-discovers associative links from sister pairs and shared lexicon glosses."""
    created_edges: list[ConceptEdge] = []

    # 1. Links from Sister Pairs (confusables & convergent notes)
    sister_stmt = select(SisterPair).where(
        SisterPair.user_id == user.id, SisterPair.status == "open"
    )
    sisters = (await db.scalars(sister_stmt)).all()

    for sp in sisters:
        cards_a = (
            await db.scalars(select(Card).where(Card.note_id == sp.note_a_id))
        ).all()
        cards_b = (
            await db.scalars(select(Card).where(Card.note_id == sp.note_b_id))
        ).all()
        rel = (
            "contrasts_with"
            if sp.kind == "interference"
            else "analogous_to"
            if sp.kind == "convergent"
            else "associative"
        )
        for ca in cards_a:
            for cb in cards_b:
                existing = await db.scalar(
                    select(ConceptEdge).where(
                        ConceptEdge.user_id == user.id,
                        ConceptEdge.source_card_id == ca.id,
                        ConceptEdge.target_card_id == cb.id,
                    )
                )
                if not existing and ca.id != cb.id:
                    edge = ConceptEdge(
                        user_id=user.id,
                        source_card_id=ca.id,
                        target_card_id=cb.id,
                        relationship_type=rel,
                        weight=1.2 if sp.kind == "interference" else 1.0,
                    )
                    db.add(edge)
                    created_edges.append(edge)

    # 2. Links from shared Lexicon Glosses
    all_cards = (
        await db.scalars(
            select(Card)
            .join(Deck, Deck.id == Card.deck_id)
            .where(Deck.user_id == user.id, Card.suspended.is_(False))
        )
    ).all()

    term_to_cards: dict[str, list[uuid.UUID]] = defaultdict(list)
    for c in all_cards:
        glosses = c.lexicon_glosses or []
        for g in glosses:
            term = g.get("term", "").lower().strip()
            if term and len(term) > 3:
                term_to_cards[term].append(c.id)

    for c_ids in term_to_cards.values():
        if 2 <= len(c_ids) <= 10:  # meaningful specific term overlap
            for i in range(len(c_ids)):
                for j in range(i + 1, min(len(c_ids), i + 3)):
                    c1, c2 = c_ids[i], c_ids[j]
                    existing = await db.scalar(
                        select(ConceptEdge).where(
                            ConceptEdge.user_id == user.id,
                            ConceptEdge.source_card_id == c1,
                            ConceptEdge.target_card_id == c2,
                        )
                    )
                    if not existing:
                        edge = ConceptEdge(
                            user_id=user.id,
                            source_card_id=c1,
                            target_card_id=c2,
                            relationship_type="associative",
                            weight=0.9,
                        )
                        db.add(edge)
                        created_edges.append(edge)

    if created_edges:
        await db.commit()
        for e in created_edges:
            await db.refresh(e)

    return created_edges
