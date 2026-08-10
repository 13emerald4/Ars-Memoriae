"""POST /api/optimize — manual FSRS parameter refit trigger (§7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Card, Deck, ReviewLog, User
from app.routers.deps import current_user
from app.services.fsrs_service import DEFAULT_PARAMETERS, FSRSService

router = APIRouter(prefix="/api", tags=["optimize"])


@router.post("/optimize")
async def optimize(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    from app.jobs.optimize_fsrs import MIN_REVIEWS_FOR_FIT, optimize_user

    reviews = await db.scalar(
        select(func.count())
        .select_from(ReviewLog)
        .join(Card, Card.id == ReviewLog.card_id)
        .join(Deck, Deck.id == Card.deck_id)
        .where(Deck.user_id == user.id)
    )
    available = FSRSService.optimizer_available()
    done = await optimize_user(db, user) if available else False

    return {
        "optimized": done,
        "review_count": int(reviews or 0),
        "min_reviews": MIN_REVIEWS_FOR_FIT,
        "optimizer_installed": available,
        "parameters": user.fsrs_parameters or DEFAULT_PARAMETERS,
        "optimized_at": user.fsrs_optimized_at,
        "reason": (
            None
            if done
            else (
                "optimizer extra not installed (rebuild with INSTALL_FSRS_OPTIMIZER=1)"
                if not available
                else f"needs at least {MIN_REVIEWS_FOR_FIT} reviews; you have {int(reviews or 0)}"
            )
        ),
    }
