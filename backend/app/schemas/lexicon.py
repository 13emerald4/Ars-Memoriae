"""Schemas for the Concordance / Lexicon subsystem."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LexiconLookupRequest(BaseModel):
    term: str = Field(..., min_length=1, max_length=120)
    context: str | None = Field(default=None, max_length=2500)
    card_id: str | None = None
    deck_name: str | None = None
    thematic_nature: str | None = None


class LexiconEntryOut(BaseModel):
    term: str
    definition: str
    context_explanation: str | None = None
    example: str | None = None
    domain: str | None = "General Studies"
    related_terms: list[str] = Field(default_factory=list)
    cached: bool = False
    model_used: str | None = None
    created_at: datetime | None = None


class RecentLexiconItem(BaseModel):
    term: str
    definition: str
    domain: str | None = None
    created_at: datetime
