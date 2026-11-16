"""Shared helpers for the part configs."""

from __future__ import annotations

import datetime as dt
from textwrap import dedent

TODAY = dt.date.today().isoformat()


def c(text: str) -> str:
    return dedent(text).strip("\n")


def note(chapters, read, solve, invariants, memory, types, failure, tests, trap, terms=()):
    return {
        "chapters": list(chapters), "read": list(read), "solve": solve, "invariants": invariants,
        "memory": memory, "types": types, "failure": failure, "tests": tests, "trap": trap,
        "terms": list(terms),
    }


COMMON_DEVIATIONS = [
    "Summary sheets: the course has no separate summary sheets, so each deck's own documentation "
    "(the summary stored with the deck in the app) is copied in its box instead.",
    "\\emph{From the readings} copies only the chapter sections each card drills (listed per card), "
    "not every section of its chapters, to keep the guide usable.",
    "The card decks were not generated anew: the guide uses the 105-card deck built earlier in this "
    "session (the same material), exported as JSON deck files alongside this guide.",
    "The skill requires a quote on every card; 68 cards had none, so verified quotes were added to the "
    "course itself (\\code{quotes.py}), where the app shows them too.",
    "Read-only cards (what does this print? / does it compile?) are typed-answer cards in the app; their "
    "\\emph{Solution} shows the verified output or compiler verdict, and their How-to-solve rows read: "
    "Solve = how to trace it, Tests = how to check it by running.",
    "Chapters follow the deck's subdeck order rather than a strict stasis order, so card and chapter "
    "numbers match the app.",
]
