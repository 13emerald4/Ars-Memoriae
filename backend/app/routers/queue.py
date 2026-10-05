"""GET /api/queue/next — the single session entry point (§7, §9).

The review UI does not need to know whether it is being handed a card or an
IR extract; that is the whole point of routing both through one endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import User
from app.routers.deps import current_user, parse_uuid
from app.schemas.review import QueueItem, SessionSummary
from app.services.queue_service import ComposedItem, compose_session

router = APIRouter(prefix="/api/queue", tags=["queue"])


def _branch_id(raw: str | None):
    """A malformed branch id is a 400, not a silently unscoped session — the
    difference between "study this branch" and "study everything" is exactly
    what the caller asked about."""
    return parse_uuid(raw, "branch") if raw else None


def to_schema(item: ComposedItem) -> QueueItem:
    return QueueItem(
        kind=item.kind,
        id=item.id,
        deck_or_source_id=item.deck_or_source_id,
        front=item.front,
        back=item.back,
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
        references=item.references,
        starter_code=item.starter_code,
        starter_tests=item.starter_tests,
        test_cases=item.test_cases,
        time_complexity=item.time_complexity,
        space_complexity=item.space_complexity,
        edge_cases=item.edge_cases,
        title=item.title,
        difficulty=item.difficulty,
        category=item.category,
    )


@router.get("/next", response_model=QueueItem | None)
async def next_item(
    response: Response,
    branch: str | None = Query(
        default=None, description="Knowledge-tree node id — study only this branch"
    ),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await compose_session(db, user, limit=1, branch=_branch_id(branch))
    if not plan.items:
        response.status_code = status.HTTP_204_NO_CONTENT
        return None
    return to_schema(plan.items[0])


@router.get("/session", response_model=SessionSummary)
async def session(
    preview: int = Query(default=25, ge=0, le=500),
    branch: str | None = Query(
        default=None, description="Knowledge-tree node id — study only this branch"
    ),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionSummary:
    """The whole composed plan: counts, caps, the §3.1 guardrail notices, and
    a preview of the upcoming items so the UI can show session progress."""
    plan = await compose_session(db, user, branch=_branch_id(branch))
    return SessionSummary(
        counts=plan.counts,
        caps=plan.caps,
        budget_seconds=plan.budget_seconds,
        notes=plan.notes,
        items=[to_schema(i) for i in plan.items[:preview]],
    )
