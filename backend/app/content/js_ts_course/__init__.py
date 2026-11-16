"""JavaScript & TypeScript: Zero to Mastery — a coding-first course.

Installed into a user's decks by ``scripts/rebuild_js_ts_deck.py``. Proved
card by card by ``tests/test_js_ts_course.py``.
"""

from __future__ import annotations

from collections.abc import Iterator

from .model import Card, CodeCard, CompileCard, Part, PredictCard, Source, Subdeck
from .part1 import PART1
from .part2 import PART2
from .part3 import PART3
from .part4 import PART4

ROOT_NAME = "JavaScript & TypeScript: Zero to Mastery"
ROOT_SUMMARY = (
    "Learn JavaScript and TypeScript by writing code. Most cards ask you to write, fix or "
    "type a small function, which is run against tests (and, for TypeScript, checked by the "
    "compiler). The rest ask what a snippet prints or whether it compiles. The why behind "
    "each answer is shown with it, with a link to MDN or the TypeScript Handbook."
)

COURSE: list[Part] = [PART1, PART2, PART3, PART4]


def iter_cards() -> Iterator[tuple[Part, Subdeck, Card]]:
    for part in COURSE:
        for subdeck in part.subdecks:
            for card in subdeck.cards:
                yield part, subdeck, card


def _attach_quotes() -> None:
    """Give every card a documentation quote (see quotes.py)."""
    from .quotes import QUOTES

    for _, _, card in iter_cards():
        if not (card.source and card.source.quote) and card.key in QUOTES:
            card.source = QUOTES[card.key]


_attach_quotes()


__all__ = [
    "COURSE",
    "ROOT_NAME",
    "ROOT_SUMMARY",
    "Card",
    "CodeCard",
    "CompileCard",
    "Part",
    "PredictCard",
    "Source",
    "Subdeck",
    "iter_cards",
]
