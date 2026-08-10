"""Sister-card interference endpoints (§2, §14 Phase 4)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Note, NoteType, SisterPair, User
from app.routers.deps import current_user, parse_uuid
from app.schemas.core import SisterPairOut
from app.services import interference_service
from app.services.rendering import render

router = APIRouter(prefix="/api/interference", tags=["interference"])


@router.post("/scan")
async def scan(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    """Recompute confusable pairs across the collection.

    Runs locally over the note text — no API calls, no cost. Dismissed pairs
    stay dismissed.
    """
    return await interference_service.scan_user(db, user)


@router.get("", response_model=list[SisterPairOut])
async def list_pairs(
    kind: str | None = Query(default=None),
    include_dismissed: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SisterPairOut]:
    stmt = select(SisterPair).where(SisterPair.user_id == user.id)
    if not include_dismissed:
        stmt = stmt.where(SisterPair.status == "open")
    if kind:
        stmt = stmt.where(SisterPair.kind == kind)
    pairs = (await db.scalars(stmt.limit(limit))).all()

    note_ids = {p.note_a_id for p in pairs} | {p.note_b_id for p in pairs}
    if not note_ids:
        return []

    rendered: dict = {}
    rows = (
        await db.execute(
            select(Note, NoteType)
            .join(NoteType, NoteType.id == Note.note_type_id)
            .where(Note.id.in_(note_ids))
        )
    ).all()
    for note, note_type in rows:
        slot = "c1" if note_type.template_kind == "cloze" else "default"
        rendered[note.id] = render(note_type.template_kind, note.field_values or {}, slot)

    out: list[SisterPairOut] = []
    for p in pairs:
        a = rendered.get(p.note_a_id, ("", ""))
        b = rendered.get(p.note_b_id, ("", ""))
        out.append(
            SisterPairOut(
                id=str(p.id),
                kind=p.kind,
                status=p.status,
                front_similarity=p.front_similarity,
                back_similarity=p.back_similarity,
                note_a_id=str(p.note_a_id),
                note_b_id=str(p.note_b_id),
                front_a=a[0],
                back_a=a[1],
                front_b=b[0],
                back_b=b[1],
            )
        )
    # Most confusable first, matching the service's own ordering.
    order = {"interference": 0, "convergent": 1, "duplicate": 2}
    out.sort(key=lambda p: (order.get(p.kind, 3), -max(p.front_similarity, p.back_similarity)))
    return out


@router.post("/{pair_id}/dismiss", response_model=SisterPairOut)
async def dismiss(
    pair_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> SisterPairOut:
    """"These two don't actually confuse me." Survives future rescans."""
    pair = await db.get(SisterPair, parse_uuid(pair_id))
    if pair is None or pair.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "pair not found")
    pair.status = "dismissed"
    await db.commit()
    return SisterPairOut(
        id=str(pair.id),
        kind=pair.kind,
        status=pair.status,
        front_similarity=pair.front_similarity,
        back_similarity=pair.back_similarity,
        note_a_id=str(pair.note_a_id),
        note_b_id=str(pair.note_b_id),
    )
