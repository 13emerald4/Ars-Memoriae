"""Extreme Atomicity Linter & Sequential Overlapping Cloze Engine.

Enforces the Minimum Information Principle (Rule of Atomicity) and provides
progressive chain clozes for multi-step processes, algorithms, and formulas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class AtomicityIssue:
    severity: Literal["info", "warning", "danger"]
    code: str
    message: str
    suggestion: str


@dataclass
class AtomicityLintResult:
    score: int  # 0 to 100
    is_atomic: bool
    word_count_front: int
    word_count_back: int
    word_count_total: int
    issues: list[AtomicityIssue] = field(default_factory=list)


def _count_words(text: str) -> int:
    """Counts alphanumeric words in text, ignoring markdown markup and html tags."""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"[#*_`~\[\]\(\)]", " ", clean)
    words = [w for w in re.split(r"\s+", clean.strip()) if w]
    return len(words)


def lint_card_atomicity(
    front: str,
    back: str,
    template_kind: str = "basic",
) -> AtomicityLintResult:
    """Evaluates a flashcard for atomicity and split-attention risks.

    Scoring (starts at 100):
      - Back word count > 15: -15 pts
      - Back word count > 25: -30 pts
      - Multiple distinct questions in front: -20 pts
      - Multiple bullet/numbered items in back: -20 pts
      - Multiple semicolons in back: -10 pts
      - Conjunction chains ("both X and Y", "as well as"): -10 pts
    """
    issues: list[AtomicityIssue] = []
    penalty = 0

    front_text = front or ""
    back_text = back or ""

    wc_front = _count_words(front_text)
    wc_back = _count_words(back_text)
    wc_total = wc_front + wc_back

    # 1. Back word count checks (Minimum Information Principle)
    if wc_back > 25:
        penalty += 35
        issues.append(
            AtomicityIssue(
                severity="danger",
                code="EXCESSIVE_BACK_LENGTH",
                message=f"Answer is {wc_back} words long (> 25 words).",
                suggestion="Atomize into single-fact retrieval targets or short phrase answers.",
            )
        )
    elif wc_back > 15:
        penalty += 15
        issues.append(
            AtomicityIssue(
                severity="warning",
                code="HIGH_BACK_LENGTH",
                message=f"Answer contains {wc_back} words (> 15 words).",
                suggestion="Trim unnecessary filler words or split into two sibling cards.",
            )
        )

    # 2. Multi-question front (Split-Attention Effect)
    question_marks = front_text.count("?")
    has_compound_interrogative = bool(
        re.search(
            r"\b(?:and\s+what|and\s+which|and\s+how|and\s+why|and\s+who|and\s+where|and\s+when)\b",
            front_text,
            re.IGNORECASE,
        )
    )
    if question_marks > 1 or has_compound_interrogative:
        penalty += 20
        issues.append(
            AtomicityIssue(
                severity="warning",
                code="MULTIPLE_QUESTIONS",
                message=f"Prompt asks multiple distinct questions (detected {max(question_marks, 2)} queries).",
                suggestion="Ask exactly one retrieval question per card to prevent partial recall lapses.",
            )
        )

    # 3. List items / enumerations in back
    bullet_matches = re.findall(r"(?:^|\n)\s*(?:[\*\-\•]|\d+[\.\)])\s+", back_text)
    if len(bullet_matches) >= 2:
        penalty += 25
        issues.append(
            AtomicityIssue(
                severity="danger",
                code="ENUMERATED_LIST",
                message=f"Answer contains a list of {len(bullet_matches)} separate items.",
                suggestion="Use Sequential Overlapping Clozes or create a separate card for each item.",
            )
        )

    # 4. Semicolons / multi-clause answers
    semicolon_count = back_text.count(";")
    if semicolon_count >= 2:
        penalty += 15
        issues.append(
            AtomicityIssue(
                severity="warning",
                code="MULTIPLE_CLAUSES",
                message=f"Answer contains {semicolon_count} semicolons dividing separate facts.",
                suggestion="Split each clause into its own individual question-answer pair.",
            )
        )

    # 5. Compound conjunction overload
    conjunction_matches = re.findall(
        r"\b(?:both\s+.+?\s+and\s+|as\s+well\s+as|furthermore|additionally|in\s+addition\s+to)\b",
        back_text,
        re.IGNORECASE,
    )
    if len(conjunction_matches) >= 2:
        penalty += 10
        issues.append(
            AtomicityIssue(
                severity="info",
                code="COMPOUND_CONJUNCTIONS",
                message="Answer joins multiple independent concepts with compound conjunctions.",
                suggestion="Test each relationship independently to prevent cognitive interference.",
            )
        )

    score = max(0, min(100, 100 - penalty))
    is_atomic = score >= 70 and not any(i.severity == "danger" for i in issues)

    return AtomicityLintResult(
        score=score,
        is_atomic=is_atomic,
        word_count_front=wc_front,
        word_count_back=wc_back,
        word_count_total=wc_total,
        issues=issues,
    )


@dataclass
class SequentialClozeCard:
    step_index: int
    total_steps: int
    front: str
    back: str
    target_step: str
    context_before: list[str]
    context_after: list[str]


def generate_sequential_clozes(
    title: str,
    steps: list[str],
    window_size: int = 1,
) -> list[SequentialClozeCard]:
    """Generates progressive overlapping chain clozes for an ordered sequence.

    For a sequence [A, B, C, D]:
      Card 1: [Step 1: A] -> Step 2: B
      Card 2: Step 1: A -> [Step 2: B] -> Step 3: C
      Card 3: Step 2: B -> [Step 3: C] -> Step 4: D
      Card 4: Step 3: C -> [Step 4: D]
    """
    clean_steps = [s.strip() for s in steps if s.strip()]
    if not clean_steps:
        return []

    cards: list[SequentialClozeCard] = []
    total = len(clean_steps)

    for i, step in enumerate(clean_steps):
        # Anchor context before (up to window_size)
        start_idx = max(0, i - window_size)
        before = clean_steps[start_idx:i]

        # Anchor context after (up to window_size)
        end_idx = min(total, i + 1 + window_size)
        after = clean_steps[i + 1 : end_idx]

        # Build clean visual front prompt
        prompt_lines = [f"**{title}** (Step {i + 1} of {total}):\n"]

        if before:
            for b_idx, b_text in enumerate(before, start=start_idx + 1):
                prompt_lines.append(f"Step {b_idx}: {b_text}")

        prompt_lines.append(f"-> **Step {i + 1}: [ ? ]**")

        if after:
            for a_idx, a_text in enumerate(after, start=i + 2):
                prompt_lines.append(f"· Step {a_idx}: {a_text}")

        front = "\n".join(prompt_lines)
        back = step

        cards.append(
            SequentialClozeCard(
                step_index=i + 1,
                total_steps=total,
                front=front,
                back=back,
                target_step=step,
                context_before=before,
                context_after=after,
            )
        )

    return cards
