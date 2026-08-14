"""The knowledge tree (SuperMemo's unified hierarchy).

One tree over decks, sources and extracts — see services/tree_service.py for
why it overlays those tables instead of replacing them.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Card, Deck, KnowledgeNode, User
from app.routers.decks import card_out
from app.routers.deps import current_user, parse_uuid
from app.schemas.core import CardOut
from app.schemas.tree import (
    BranchSummary,
    NodeMove,
    NodeUpdate,
    TopicCreate,
    TreeNodeOut,
    TreeOut,
)
from app.services import tree_service

router = APIRouter(prefix="/api/tree", tags=["knowledge-tree"])


async def _owned_node(db: AsyncSession, user: User, node_id: uuid.UUID) -> KnowledgeNode:
    node = await db.get(KnowledgeNode, node_id)
    if node is None or node.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "node not found")
    return node


def _to_schema(view: tree_service.TreeNodeView) -> TreeNodeOut:
    n = view.node
    return TreeNodeOut(
        id=str(n.id),
        parent_id=str(n.parent_id) if n.parent_id else None,
        kind=n.kind,
        title=view.title,
        position=n.position,
        collapsed=n.collapsed,
        priority=view.priority,
        priority_inherited=view.priority_inherited,
        card_count=view.counts.cards,
        due_count=view.counts.due,
        new_count=view.counts.new,
        extract_count=view.counts.extracts,
        deck_id=str(n.deck_id) if n.deck_id else None,
        source_id=str(n.source_id) if n.source_id else None,
        extract_id=str(n.extract_id) if n.extract_id else None,
        mastery_pct=view.mastery_pct,
        locked=view.locked,
        requires_node_id=str(n.requires_node_id) if n.requires_node_id else None,
        requires_title=view.requires_title,
        mastery_threshold=n.mastery_threshold,
        children=[_to_schema(c) for c in view.children],
    )


@router.get("", response_model=TreeOut)
async def get_tree(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> TreeOut:
    """The whole tree, with counts rolled up through each branch.

    Decks, sources and extracts that predate the tree (or arrived through the
    Anki importer, which knows nothing about it) are given nodes here on first
    read — see tree_service.ensure_tree.
    """
    views = await tree_service.build_tree(db, user)
    return TreeOut(nodes=[_to_schema(v) for v in views])


@router.post("/nodes", response_model=TreeNodeOut, status_code=201)
async def create_topic(
    body: TopicCreate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> TreeNodeOut:
    """Add a grouping branch. Topics are the only node kind created directly —
    the others appear when their deck or source does."""
    parent_id = None
    if body.parent_id:
        parent = await _owned_node(db, user, parse_uuid(body.parent_id, "parent_id"))
        parent_id = parent.id
    node = await tree_service.create_topic(
        db, user, title=body.title, parent_id=parent_id, priority=body.priority
    )
    await db.commit()
    await db.refresh(node)
    nodes = await tree_service.load_nodes(db, user)
    priority, inherited = tree_service.resolve_priority(nodes, node)
    return TreeNodeOut(
        id=str(node.id),
        parent_id=str(node.parent_id) if node.parent_id else None,
        kind=node.kind,
        title=node.title,
        position=node.position,
        collapsed=node.collapsed,
        priority=priority,
        priority_inherited=inherited,
    )


@router.patch("/nodes/{node_id}")
async def update_node(
    node_id: str,
    body: NodeUpdate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Rename, collapse, or re-prioritise — optionally down the whole branch."""
    node = await _owned_node(db, user, parse_uuid(node_id))
    entities_touched = 0

    if body.title is not None:
        node.title = body.title.strip()
        # An entity node's title is the entity's name; keep them in step rather
        # than letting the tree drift from the Decks page.
        if node.deck_id:
            deck = await db.get(Deck, node.deck_id)
            if deck is not None:
                deck.name = node.title
        elif node.source_id:
            from app.models import Source

            source = await db.get(Source, node.source_id)
            if source is not None:
                source.title = node.title
    if body.collapsed is not None:
        node.collapsed = body.collapsed
    if body.priority is not None:
        entities_touched = await tree_service.set_priority(
            db, user, node, body.priority, cascade=body.cascade
        )

    # requires_node_id follows parent_id's convention elsewhere in this
    # router: absent means "leave alone," present-and-null means "clear."
    # mastery_threshold can be adjusted on its own even without touching the
    # prerequisite, so it isn't gated behind the same presence check.
    data = body.model_dump(exclude_unset=True)
    if "requires_node_id" in data or body.mastery_threshold is not None:
        raw = data.get("requires_node_id", "__unset__")
        threshold = body.mastery_threshold if body.mastery_threshold is not None else node.mastery_threshold
        target_id = None
        if raw == "__unset__":
            target_id = node.requires_node_id
        elif raw:
            target = await _owned_node(db, user, parse_uuid(raw, "requires_node_id"))
            target_id = target.id
        try:
            await tree_service.set_prerequisite(db, user, node, target_id, threshold)
        except tree_service.TreeError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    await db.commit()
    return {
        "id": str(node.id),
        "title": node.title,
        "priority": node.priority,
        "collapsed": node.collapsed,
        "requires_node_id": str(node.requires_node_id) if node.requires_node_id else None,
        "mastery_threshold": node.mastery_threshold,
        "entities_updated": entities_touched,
    }


@router.post("/nodes/{node_id}/move")
async def move_node(
    node_id: str,
    body: NodeMove,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    node = await _owned_node(db, user, parse_uuid(node_id))
    parent_id = None
    if body.parent_id:
        parent = await _owned_node(db, user, parse_uuid(body.parent_id, "parent_id"))
        parent_id = parent.id
    try:
        await tree_service.move(db, user, node, parent_id, body.position)
    except tree_service.TreeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    await db.commit()
    return {"id": str(node.id), "parent_id": str(node.parent_id) if node.parent_id else None}


@router.delete("/nodes/{node_id}", status_code=200)
async def delete_node(
    node_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    """Delete a topic. Its children move up to its parent — deleting a grouping
    node must never take study material with it."""
    node = await _owned_node(db, user, parse_uuid(node_id))
    try:
        promoted = await tree_service.delete_topic(db, user, node)
    except tree_service.TreeError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    await db.commit()
    return {"deleted": str(node_id), "children_promoted": promoted}


@router.get("/nodes/{node_id}/branch", response_model=BranchSummary)
async def branch(
    node_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> BranchSummary:
    """What a branch-scoped session would draw from."""
    scope = await tree_service.branch_scope(db, user, parse_uuid(node_id))
    if scope is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "node not found")
    return BranchSummary(
        node_id=str(scope.node_id),
        title=scope.title,
        deck_count=len(scope.deck_ids),
        extract_count=len(scope.extract_ids),
    )


@router.get("/nodes/{node_id}/cards", response_model=list[CardOut])
async def branch_cards(
    node_id: str,
    limit: int = 100,
    include_suspended: bool = False,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CardOut]:
    """The cards living under a branch — a deck's cards, plus anything carved
    out of the extracts in it."""
    scope = await tree_service.branch_scope(db, user, parse_uuid(node_id))
    if scope is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "node not found")
    if scope.empty:
        return []

    from sqlalchemy import or_

    reachable = []
    if scope.deck_ids:
        reachable.append(Card.deck_id.in_(scope.deck_ids))
    if scope.extract_ids:
        reachable.append(Card.origin_extract_id.in_(scope.extract_ids))

    stmt = (
        select(Card)
        .join(Deck, Deck.id == Card.deck_id)
        .where(Deck.user_id == user.id, or_(*reachable))
        .order_by(Card.due.is_(None), Card.due)
        .limit(max(1, min(limit, 500)))
    )
    if not include_suspended:
        stmt = stmt.where(Card.suspended.is_(False))
    return [card_out(c) for c in (await db.scalars(stmt)).all()]
