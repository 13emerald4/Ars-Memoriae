"""Document upload -> LLM-generated deck with citations back into the reading."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentOut(BaseModel):
    source_id: str
    title: str
    segment_count: int
    locators: list[str] = Field(default_factory=list)  # a sample, for the UI
    node_id: str | None = None


class CitedCard(BaseModel):
    """A proposed card plus where in the document it came from.

    Nothing here is persisted until the user accepts it — same
    propose-then-confirm shape as LLM grading and IR card generation.
    """

    kind: str = "qa"  # "qa" | "cloze"
    front: str = ""
    back: str = ""
    cloze_text: str | None = None
    quote: str = ""
    # False when the quote could not be found in the source passage — a
    # hallucinated citation, which the UI must not present as a real one.
    quote_verified: bool = False
    locator: str | None = None
    extract_id: str | None = None


class GenerateDeckRequest(BaseModel):
    max_cards_per_section: int = Field(default=3, ge=1, le=10)
    # Bounded because each section is one LLM round trip; a 400-page textbook
    # would otherwise be 400 calls behind a single button press.
    max_sections: int = Field(default=15, ge=1, le=100)
    start_section: int = Field(default=0, ge=0)
    model: str | None = None


class GenerateDeckResponse(BaseModel):
    source_id: str
    title: str
    cards: list[CitedCard] = Field(default_factory=list)
    sections_used: int = 0
    sections_total: int = 0
    next_section: int | None = None
    degraded: bool = False
    reason: str | None = None
    warnings: list[str] = Field(default_factory=list)


class AcceptDeckRequest(BaseModel):
    deck: str = Field(min_length=1, max_length=200)
    cards: list[CitedCard] = Field(min_length=1, max_length=1000)
    priority: int | None = Field(default=None, ge=0, le=100)


class AcceptDeckResponse(BaseModel):
    deck_id: str
    deck_created: bool
    notes_created: int
    cards_created: int
    references_created: int
    warnings: list[str] = Field(default_factory=list)


class CardReferenceOut(BaseModel):
    quote: str
    quote_verified: bool
    locator: str | None = None
    source_title: str | None = None
    extract_id: str | None = None
    # The full passage the card came from — what the reader actually wants
    # when the quote alone isn't enough context.
    passage: str | None = None
