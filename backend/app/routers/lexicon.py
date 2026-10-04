"""Router for the technical lexicon and concordance subsystem."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import User
from app.routers.deps import current_user, optional_user
from app.schemas.lexicon import LexiconEntryOut, LexiconLookupRequest, RecentLexiconItem
from app.services import lexicon_service

router = APIRouter(prefix="/api/lexicon", tags=["lexicon"])


@router.post("/lookup", response_model=LexiconEntryOut)
async def lookup_term(
    body: LexiconLookupRequest,
    user: User | None = Depends(optional_user),
    db: AsyncSession = Depends(get_db),
) -> LexiconEntryOut:
    """Look up a technical term, concept, or phrase with contextual explanation."""
    data = await lexicon_service.lookup_term(
        db,
        term=body.term,
        context=body.context,
        user=user,
    )
    return LexiconEntryOut(**data)


@router.get("/recent", response_model=list[RecentLexiconItem])
async def recent_terms(
    user: User | None = Depends(optional_user),
    db: AsyncSession = Depends(get_db),
) -> list[RecentLexiconItem]:
    """Return recently explored vocabulary terms for concordance exploration."""
    items = await lexicon_service.get_recent_terms(db, limit=20)
    return [RecentLexiconItem(**it) for it in items]
