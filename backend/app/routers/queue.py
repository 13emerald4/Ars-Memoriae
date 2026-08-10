"""GET /api/queue/next — the single session entry point (§7, §9).

The review UI does not need to know whether it is being handed a card or an
IR extract; that is the whole point of routing both through one endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import User
from app.routers.deps import current_user
from app.schemas.review import QueueItem, SessionSummary
from app.services.queue_service import ComposedItem, compose_session

router = APIRouter(prefix="/api/queue", tags=["queue"])


def to_schema(item: ComposedItem) -> QueueItem:
    return QueueItem(
        kind=item.kind,
        id=item.id,
        deck_or_source_id=item.deck_or_source_id,
        front=item.front,
        extract_content=item.extract_content,
        priority=item.priority,
        effective_priority=round(item.effective_priority, 2),
        deck_name=item.deck_name,
        source_title=item.source_title,
        state=item.state,
        template_kind=item.template_kind,
        grading_profile=item.grading_profile,
        note_id=item.note_id,
        occlusion=item.occlusion,
    )


@router.get("/next", response_model=QueueItem | None)
async def next_item(
    response: Response, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
):
    plan = await compose_session(db, user, limit=1)
    if not plan.items:
        response.status_code = status.HTTP_204_NO_CONTENT
        return None
    return to_schema(plan.items[0])


@router.get("/session", response_model=SessionSummary)
async def session(
    preview: int = Query(default=25, ge=0, le=500),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionSummary:
    """The whole composed plan: counts, caps, the §3.1 guardrail notices, and
    a preview of the upcoming items so the UI can show session progress."""
    plan = await compose_session(db, user)
    return SessionSummary(
        counts=plan.counts,
        caps=plan.caps,
        budget_seconds=plan.budget_seconds,
        notes=plan.notes,
        items=[to_schema(i) for i in plan.items[:preview]],
    )
