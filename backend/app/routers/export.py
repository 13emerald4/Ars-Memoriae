"""GET /api/export — full-fidelity JSON dump (§7, §10).

Data ownership is a first-class feature here, not a promise: this returns
everything needed to rebuild the account elsewhere — decks, note types, notes,
cards with their live FSRS state, the complete review log, and IR sources and
extracts. It is available on a hosted instance too, which is the whole point.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import (
    Card,
    Deck,
    Extract,
    Import,
    MediaAsset,
    Note,
    NoteType,
    QueueConfig,
    ReviewLog,
    Source,
    StudySession,
    User,
)
from app.routers.deps import current_user
from app.services.queue_service import get_queue_config

router = APIRouter(prefix="/api", tags=["export"])

EXPORT_VERSION = 1


def _iso(value):
    return value.isoformat() if isinstance(value, datetime) else value


@router.get("/export")
async def export_all(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> StreamingResponse:
    decks = (await db.scalars(select(Deck).where(Deck.user_id == user.id))).all()
    note_types = (await db.scalars(select(NoteType).where(NoteType.user_id == user.id))).all()
    notes = (await db.scalars(select(Note).where(Note.user_id == user.id))).all()
    note_ids = [n.id for n in notes]

    cards = (
        (await db.scalars(select(Card).where(Card.note_id.in_(note_ids)))).all() if note_ids else []
    )
    card_ids = [c.id for c in cards]
    logs = (
        (
            await db.scalars(
                select(ReviewLog)
                .where(ReviewLog.card_id.in_(card_ids))
                .order_by(ReviewLog.reviewed_at)
            )
        ).all()
        if card_ids
        else []
    )
    media = (
        (await db.scalars(select(MediaAsset).where(MediaAsset.note_id.in_(note_ids)))).all()
        if note_ids
        else []
    )
    sources = (await db.scalars(select(Source).where(Source.user_id == user.id))).all()
    source_ids = [s.id for s in sources]
    extracts = (
        (await db.scalars(select(Extract).where(Extract.source_id.in_(source_ids)))).all()
        if source_ids
        else []
    )
    imports = (await db.scalars(select(Import).where(Import.user_id == user.id))).all()
    study_sessions = (
        await db.scalars(
            select(StudySession)
            .where(StudySession.user_id == user.id)
            .order_by(StudySession.started_at)
        )
    ).all()
    cfg: QueueConfig = await get_queue_config(db, user)

    payload = {
        "export_version": EXPORT_VERSION,
        "exported_at": datetime.now().astimezone().isoformat(),
        "user": {
            "id": str(user.id),
            "email": user.email,
            "desired_retention": user.desired_retention,
            "grading_model": user.grading_model,
            "queue_time_budget_minutes": user.queue_time_budget_minutes,
            "daily_new_limit": user.daily_new_limit,
            "daily_review_limit": user.daily_review_limit,
            "backlog_spread_days": user.backlog_spread_days,
            "leech_threshold": user.leech_threshold,
            "leech_remediation_opt_in": user.leech_remediation_opt_in,
            "llm_grading_consent": user.llm_grading_consent,
            "grading_bias": user.grading_bias,
            "fsrs_parameters": user.fsrs_parameters,
            "fsrs_optimized_at": _iso(user.fsrs_optimized_at),
            # The stored Google API key is deliberately NOT exported.
        },
        "queue_config": {
            "review_weight": cfg.review_weight,
            "new_weight": cfg.new_weight,
            "ir_weight": cfg.ir_weight,
            "seconds_per_review": cfg.seconds_per_review,
            "seconds_per_ir_extract": cfg.seconds_per_ir_extract,
        },
        "decks": [
            {
                "id": str(d.id),
                "parent_id": str(d.parent_id) if d.parent_id else None,
                "name": d.name,
                "desired_retention_override": d.desired_retention_override,
                "default_priority": d.default_priority,
                "created_at": _iso(d.created_at),
            }
            for d in decks
        ],
        "note_types": [
            {
                "id": str(n.id),
                "name": n.name,
                "template_kind": n.template_kind,
                "fields": n.fields,
                "grading_profile": n.grading_profile,
            }
            for n in note_types
        ],
        "notes": [
            {
                "id": str(n.id),
                "note_type_id": str(n.note_type_id),
                "field_values": n.field_values,
                "created_at": _iso(n.created_at),
            }
            for n in notes
        ],
        "cards": [
            {
                "id": str(c.id),
                "note_id": str(c.note_id),
                "deck_id": str(c.deck_id),
                "template_slot": c.template_slot,
                "state": c.state,
                "stability": c.stability,
                "difficulty": c.difficulty,
                "step": c.step,
                "due": _iso(c.due),
                "last_review": _iso(c.last_review),
                "priority": c.priority,
                "origin": c.origin,
                "origin_extract_id": str(c.origin_extract_id) if c.origin_extract_id else None,
                "lapse_count": c.lapse_count,
                "leech_flag": c.leech_flag,
                "suspended": c.suspended,
                "tags": list(c.tags or []),
            }
            for c in cards
        ],
        "review_logs": [
            {
                "id": r.id,
                "card_id": str(r.card_id),
                "reviewed_at": _iso(r.reviewed_at),
                "typed_answer": r.typed_answer,
                "latency_ms": r.latency_ms,
                "llm_grade": r.llm_grade,
                "llm_reasoning": r.llm_reasoning,
                "llm_confidence": r.llm_confidence,
                "final_grade": r.final_grade,
                "overridden": r.overridden,
                "state_before": r.state_before,
                "elapsed_days": r.elapsed_days,
                "graduated_to_review": r.graduated_to_review,
            }
            for r in logs
        ],
        "media_assets": [
            {
                "id": str(m.id),
                "note_id": str(m.note_id),
                "kind": m.kind,
                "storage_path": m.storage_path,
                "original_name": m.original_name,
            }
            for m in media
        ],
        "sources": [
            {
                "id": str(s.id),
                "title": s.title,
                "raw_text": s.raw_text,
                "url": s.url,
                "priority": s.priority,
                "status": s.status,
                "created_at": _iso(s.created_at),
            }
            for s in sources
        ],
        "extracts": [
            {
                "id": str(e.id),
                "source_id": str(e.source_id),
                "content": e.content,
                "priority": e.priority,
                "position": e.position,
                "next_shown_at": _iso(e.next_shown_at),
                "status": e.status,
            }
            for e in extracts
        ],
        "imports": [
            {
                "id": str(i.id),
                "filename": i.filename,
                "imported_at": _iso(i.imported_at),
                "notes_mapped": i.notes_mapped,
                "cards_mapped": i.cards_mapped,
                "warnings": i.warnings,
            }
            for i in imports
        ],
        "study_sessions": [
            {
                "id": str(s.id),
                "started_at": _iso(s.started_at),
                "ended_at": _iso(s.ended_at),
                "planned_seconds": s.planned_seconds,
                "active_seconds": s.active_seconds,
                "focus_goal": s.focus_goal,
                "goal_cards": s.goal_cards,
                "cards_reviewed": s.cards_reviewed,
                "banked_seconds": s.banked_seconds,
                "distraction": s.distraction,
                "next_time_plan": s.next_time_plan,
            }
            for s in study_sessions
        ],
    }

    import json

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    async def stream():
        # Chunked so a large collection doesn't materialise twice in memory.
        text = json.dumps(payload, indent=2, ensure_ascii=False)
        for i in range(0, len(text), 65536):
            yield text[i : i + 65536].encode()

    return StreamingResponse(
        stream(),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="memorization-export-{stamp}.json"'},
    )


@router.get("/export/review-logs.csv")
async def export_review_logs_csv(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> StreamingResponse:
    """Mnemosyne's "personal science" angle (§2): raw review logs as CSV, so
    the data is usable in a notebook without parsing the full JSON dump."""
    rows = (
        await db.execute(
            select(ReviewLog, Card.template_slot, Deck.name)
            .join(Card, Card.id == ReviewLog.card_id)
            .join(Deck, Deck.id == Card.deck_id)
            .where(Deck.user_id == user.id)
            .order_by(ReviewLog.reviewed_at)
        )
    ).all()

    async def stream():
        yield (
            b"reviewed_at,card_id,deck,slot,final_grade,llm_grade,llm_confidence,"
            b"overridden,latency_ms,state_before,elapsed_days,graduated_to_review\n"
        )
        for log, slot, deck_name in rows:
            yield (
                f"{_iso(log.reviewed_at)},{log.card_id},"
                f'"{(deck_name or "").replace(chr(34), chr(34) * 2)}",{slot},'
                f"{log.final_grade},{log.llm_grade or ''},{log.llm_confidence or ''},"
                f"{int(log.overridden)},{log.latency_ms or ''},{log.state_before or ''},"
                f"{log.elapsed_days if log.elapsed_days is not None else ''},"
                f"{int(log.graduated_to_review)}\n"
            ).encode()

    return StreamingResponse(
        stream(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="review-logs.csv"'},
    )
