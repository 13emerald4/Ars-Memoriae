"""Export the course as JSON deck files the app's JSON import accepts.

One plain array per subdeck (``NN-name.json``) plus a wrapped copy
(``NN-name.wrapped.json``: ``{"deck", "priority", "notes"}``) for
``POST /api/import/json``. Code cards become ``card_type: "code"``; predict
and compile cards become ``card_type: "qa"``. Every card carries its verified
documentation quote.

The canonical installer is ``backend/scripts/rebuild_js_ts_deck.py``, which
also builds the deck tree; these files are the portable copy.

Usage (from the repo root): backend/.venv/bin/python study-guides/js-ts/source/export_decks.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "backend"))

from app.content.js_ts_course import COURSE, ROOT_NAME  # noqa: E402
from app.content.js_ts_course.model import CodeCard  # noqa: E402
from app.content.js_ts_course.render import card_fields, card_tags  # noqa: E402

PRIORITY = 50


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def note_json(card, category: str) -> dict:
    fields = card_fields(card, category)
    base = {
        "front": fields["Front"],
        "back": fields["Back"],
        "quote": card.source.quote,
        "locator": card.source.title,
        "source_title": card.source.title,
        "tags": card_tags(card),
    }
    if not isinstance(card, CodeCard):
        return {"card_type": "qa", **base}
    out = {
        "card_type": "code",
        "title": card.title,
        "category": category,
        "difficulty": card.difficulty,
        **base,
        "language": card.language,
        "starter_code": card.starter,
        "test_cases": card.tests,
    }
    if card.type_check:
        out["type_check"] = True
        if card.type_tests:
            out["type_tests"] = card.type_tests
    return out


def main() -> None:
    out = HERE.parent / "decks"
    out.mkdir(parents=True, exist_ok=True)
    index = []
    for part in COURSE:
        part_dir = out / slug(part.name)
        part_dir.mkdir(exist_ok=True)
        for subdeck in part.subdecks:
            notes = [note_json(card, subdeck.name) for card in subdeck.cards]
            assert all(n["quote"].strip() for n in notes), subdeck.name
            name = slug(subdeck.name)
            deck = f"{ROOT_NAME} · {subdeck.name}"
            (part_dir / f"{name}.json").write_text(json.dumps(notes, ensure_ascii=False, indent=2) + "\n")
            wrapped = {"deck": deck, "priority": PRIORITY, "notes": notes}
            (part_dir / f"{name}.wrapped.json").write_text(
                json.dumps(wrapped, ensure_ascii=False, indent=2) + "\n"
            )
            code = sum(n["card_type"] == "code" for n in notes)
            index.append((part.name, subdeck.name, code, len(notes) - code))
    total_code = sum(r[2] for r in index)
    total_qa = sum(r[3] for r in index)
    for row in index:
        print(f"{row[0]} | {row[1]} | code {row[2]} | qa {row[3]}")
    print(f"total: {total_code + total_qa} cards ({total_code} code, {total_qa} qa)")


if __name__ == "__main__":
    main()
