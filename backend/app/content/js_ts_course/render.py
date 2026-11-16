"""Turns course cards into the note fields the app stores and grades.

Code cards become "code exercise" notes (math_code profile) with starter code
and test cases, exactly like a JSON-imported code card. Predict and compile
cards are basic notes whose back starts with the exact answer; their back
holds no code fence, so the review screen treats them as typed-answer cards.
"""

from __future__ import annotations

import textwrap

from .model import CodeCard, CompileCard, PredictCard, Source

COURSE_TAG = "js-ts-course"


def _fence(language: str) -> str:
    return "ts" if language == "typescript" else "js"


def _why_comment(card: CodeCard) -> str:
    lines = textwrap.wrap(f"Why: {card.why}", width=88)
    if card.source:
        lines.append(f"Docs: {card.source.url}")
    return "\n".join(f"// {line}" for line in lines)


def _docs_line(source: Source | None) -> str:
    return f"\n\nDocs: {source.title} — {source.url}" if source else ""


def code_fields(card: CodeCard, category: str) -> dict:
    # The whole starter, as given: a fix card's bug and a driver the tests
    # rely on must both be visible (the shared front formatter trims both).
    front = f"**{card.title}**\n\n{card.task}\n\n```{_fence(card.language)}\n{card.starter.rstrip()}\n```"
    fields = {
        "Front": front,
        "Back": f"{_why_comment(card)}\n{card.solution}",
        "title": card.title,
        "language": card.language,
        "starter_code": card.starter,
        "test_cases": card.tests,
        "difficulty": card.difficulty,
        "category": category,
    }
    if card.type_check:
        fields["type_check"] = True
        if card.type_tests:
            fields["type_tests"] = card.type_tests
    return fields


def predict_fields(card: PredictCard) -> dict:
    fence = _fence(card.language)
    if card.files:
        shown = "".join(
            f"`{name}`\n```{fence}\n{body.rstrip()}\n```\n\n" for name, body in card.files.items()
        )
        main = "main.ts" if card.language == "typescript" else "main.js"
        front = f"What does running `{main}` print?\n\n{shown}`{main}`\n```{fence}\n{card.snippet.rstrip()}\n```"
    else:
        question = card.prompt or "What does this print?"
        front = f"{question}\n\n```{fence}\n{card.snippet.rstrip()}\n```"
    back = f"{card.output}\n\nWhy: {card.why}{_docs_line(card.source)}"
    return {"Front": front, "Back": back}


def compile_fields(card: CompileCard) -> dict:
    flags = "".join(f" `--{name}`" for name in card.options)
    front = (
        f"Does this compile with `tsc --strict`{flags}? If not, which statement fails, and why?"
        f"\n\n```ts\n{card.snippet.rstrip()}\n```"
    )
    back = f"{card.answer}\n\nWhy: {card.why}{_docs_line(card.source)}"
    return {"Front": front, "Back": back}


def card_kind(card) -> str:
    if isinstance(card, CodeCard):
        return card.kind
    return "predict" if isinstance(card, PredictCard) else "compile"


def card_fields(card, category: str) -> dict:
    if isinstance(card, CodeCard):
        return code_fields(card, category)
    if isinstance(card, PredictCard):
        return predict_fields(card)
    if isinstance(card, CompileCard):
        return compile_fields(card)
    raise TypeError(f"unknown card type: {type(card).__name__}")


def card_tags(card) -> list[str]:
    tags = [COURSE_TAG, card_kind(card), card.key]
    if isinstance(card, CodeCard):
        tags.append("code")
    return tags
