"""Associative Graph & Spreading Activation endpoints (§Neuroscience)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Card, User
from app.routers.deps import current_user, parse_uuid
from app.schemas.graph import (
    AutoLinkResult,
    ConceptEdgeCreate,
    ConceptEdgeOut,
    ConceptGraphOut,
    SpreadingActivationNode,
    SpreadingActivationResponse,
)
from app.services import graph_service
from app.services.rendering import render

router = APIRouter(prefix="/api/graph", tags=["associative-graph"])


@router.get("", response_model=ConceptGraphOut)
async def get_concept_graph(
    deck_id: str | None = Query(default=None),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> ConceptGraphOut:
    """Returns the user's associative knowledge network (nodes and semantic edges)."""
    d_uuid = parse_uuid(deck_id, "deck_id") if deck_id else None
    data = await graph_service.get_graph(db, user, d_uuid)
    return ConceptGraphOut(**data)


@router.post("/edges", response_model=ConceptEdgeOut, status_code=201)
async def create_concept_edge(
    body: ConceptEdgeCreate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> ConceptEdgeOut:
    """Creates or updates a semantic association edge between two cards."""
    src = parse_uuid(body.source_card_id, "source_card_id")
    tgt = parse_uuid(body.target_card_id, "target_card_id")

    card_a = await db.get(Card, src)
    card_b = await db.get(Card, tgt)
    if not card_a or not card_b:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "source or target card not found")

    try:
        edge = await graph_service.create_edge(
            db,
            user,
            src,
            tgt,
            relationship_type=body.relationship_type,
            weight=body.weight,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))

    return ConceptEdgeOut(
        id=str(edge.id),
        source_card_id=str(edge.source_card_id),
        target_card_id=str(edge.target_card_id),
        relationship_type=edge.relationship_type,
        weight=edge.weight,
        created_at=edge.created_at,
    )


@router.delete("/edges/{edge_id}", status_code=204)
async def delete_concept_edge(
    edge_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    deleted = await graph_service.delete_edge(db, user, parse_uuid(edge_id, "edge_id"))
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "edge not found")


@router.get("/related/{card_id}", response_model=SpreadingActivationResponse)
async def get_related_cards_via_spreading_activation(
    card_id: str,
    decay: float = Query(default=0.6, ge=0.1, le=0.9),
    depth: int = Query(default=2, ge=1, le=4),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> SpreadingActivationResponse:
    """Computes spreading activation energy traversing outward across associative edges."""
    c_uuid = parse_uuid(card_id, "card_id")
    card = await db.get(Card, c_uuid)
    if not card:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "card not found")

    front, _ = render(
        card.note.note_type.template_kind,
        card.note.field_values or {},
        card.template_slot,
    )
    source_title = " ".join(front.split())[:60] if front else f"Card {str(card.id)[:8]}"

    activated = await graph_service.spreading_activation(
        db, user, c_uuid, decay=decay, max_depth=depth
    )

    return SpreadingActivationResponse(
        source_card_id=str(card.id),
        source_title=source_title,
        activated_nodes=[SpreadingActivationNode(**item) for item in activated],
    )


@router.post("/auto-link", response_model=AutoLinkResult)
async def auto_discover_associative_edges(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> AutoLinkResult:
    """Auto-discovers semantic edges from confusable sister pairs and shared lexicon glosses."""
    created = await graph_service.auto_discover_edges(db, user)
    return AutoLinkResult(
        created_count=len(created),
        edges=[
            ConceptEdgeOut(
                id=str(e.id),
                source_card_id=str(e.source_card_id),
                target_card_id=str(e.target_card_id),
                relationship_type=e.relationship_type,
                weight=e.weight,
                created_at=e.created_at,
            )
            for e in created
        ],
    )
