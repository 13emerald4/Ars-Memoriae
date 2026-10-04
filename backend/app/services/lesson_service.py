"""Learn & Practice — teach the idea before testing recall.

The mode exists because a spaced-repetition queue is a *testing* instrument:
it assumes you already learned the material somewhere else. For cards carved
out of an uploaded document that assumption is often false — the card was
generated from a passage the user may never have read closely. So before the
question, this hands them the passage's idea in a couple of paragraphs.

Two rules shape everything here:

**A lesson needs a citation.** Cards without a :class:`CardReference` are not
teachable and say so, rather than having an explanation invented for them. The
user is reading a lesson precisely because they don't yet know the material,
which is exactly the position from which a confident fabrication does the most
damage.

**No key is a full path, not an error.** Without consent or an API key the
cited passage itself is shown, labelled as the raw source. That's a genuinely
useful "read this first" step, and it matches how grading degrades (§4.3).
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_api_key
from app.models import Card, CardLesson, CardReference, Extract, User
from app.services.grading_service import GradingService, GradingUnavailable
from app.services.rendering import render

log = logging.getLogger(__name__)

# Enough to teach one idea, short enough to read before answering. A lesson
# longer than the passage it summarises is not a lesson.
LESSON_MAX_WORDS = 160


async def _citations(db: AsyncSession, card: Card) -> list[dict]:
    rows = (
        await db.execute(
            select(CardReference, Extract.content)
            .outerjoin(Extract, Extract.id == CardReference.extract_id)
            .where(CardReference.card_id == card.id)
            .order_by(CardReference.position, CardReference.created_at)
        )
    ).all()
    return [
        {
            "quote": ref.quote or "",
            "quote_verified": ref.quote_verified,
            "locator": ref.locator,
            "source_title": ref.source_title,
            "extract_id": str(ref.extract_id) if ref.extract_id else None,
            "passage": passage,
        }
        for ref, passage in rows
    ]


def _teaching_text(citations: list[dict]) -> list[str]:
    """What the model is allowed to teach from.

    The full extract is preferred over the quote: a quote is the single span
    that contains the *answer*, which is too narrow to explain anything. The
    surrounding passage is what carries the reasoning.
    """
    out: list[str] = []
    for c in citations:
        text = (c.get("passage") or "").strip() or (c.get("quote") or "").strip()
        if text:
            out.append(text)
    return out


def _fallback_body(citations: list[dict]) -> str:
    parts = []
    for c in citations:
        text = (c.get("passage") or "").strip() or (c.get("quote") or "").strip()
        if not text:
            continue
        where = c.get("locator") or c.get("source_title")
        parts.append(f"{where}\n\n{text}" if where else text)
    return "\n\n———\n\n".join(parts)


async def get_lesson(db: AsyncSession, user: User, card: Card) -> dict:
    """The lesson for one card, generating and caching it on first request."""
    citations = await _citations(db, card)
    if not citations:
        return {
            "available": False,
            "reason": "no_citations",
            "body": "",
            "key_points": [],
            "generated": False,
            "model_used": None,
            "cached": False,
            "citations": [],
        }

    cached = await db.get(CardLesson, card.id)
    if cached is not None:
        return {
            "available": True,
            "reason": None,
            "body": cached.body,
            "key_points": list(cached.key_points or []),
            "generated": True,
            "model_used": cached.model_used,
            "cached": True,
            "citations": citations,
        }

    def source_only(reason: str | None) -> dict:
        return {
            "available": True,
            "reason": reason,
            "body": _fallback_body(citations),
            "key_points": [],
            "generated": False,
            "model_used": None,
            "cached": False,
            "citations": citations,
        }

    # Deliberately not cached: a fallback is a stand-in for a lesson that
    # couldn't be written yet, so adding a key later should produce the real
    # thing rather than replay a stale substitute forever.
    if not user.llm_grading_consent:
        return source_only("consent_not_given")
    api_key = decrypt_api_key(user.google_api_key_encrypted)

    note = card.note
    front, back = render(
        note.note_type.template_kind, note.field_values or {}, card.template_slot
    )
    model = user.grading_model
    try:
        result = await GradingService(api_key, model).generate_lesson(
            front=front,
            back=back,
            passages=_teaching_text(citations),
            max_words=LESSON_MAX_WORDS,
        )
    except GradingUnavailable as exc:
        log.info("lesson generation unavailable for card %s: %s", card.id, exc)
        return source_only(str(exc))

    db.add(
        CardLesson(
            card_id=card.id,
            body=result["lesson"],
            key_points=result["key_points"],
            model_used=model,
        )
    )
    await db.commit()

    return {
        "available": True,
        "reason": None,
        "body": result["lesson"],
        "key_points": result["key_points"],
        "generated": True,
        "model_used": model,
        "cached": False,
        "citations": citations,
    }
