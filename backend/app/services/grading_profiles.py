"""Per-card-type grading rubric profiles (§4.5).

Each profile is a prompt template — not a separate model or pipeline — merged
into the base rubric from §4.4, so adding a profile stays cheap. Selection is
routed through the strategy registry (§12) so this is one of the seams a
plugin can later override.
"""

from __future__ import annotations

BASE_PROMPT = """You are grading a spaced-repetition flashcard answer. Compare the
user's answer to the reference answer. Judge semantic correctness, not
exact wording. Output must match the provided JSON schema.

Card front: {front}
Reference answer: {back}
User's answer: {user_answer}
Response time: {latency_ms} ms
Card type: {card_type}

Grade on this exact 4-point scale:
- again: wrong, or no meaningful recall
- hard: correct but with significant hesitation/errors/omissions
- good: correct with minor omissions
- easy: correct, complete, confident

{rubric}

Respond with ONLY a JSON object of this shape, no prose and no code fences:
{{"grade": "again|hard|good|easy", "confidence": 0.0-1.0,
  "matched_points": ["..."], "missed_points": ["..."], "reasoning": "one or two sentences"}}
"""

SHORT_ANSWER_RUBRIC = """Rubric (short answer / vocabulary):
- Reward an exact match or a close paraphrase of the key term equally.
- Accept synonyms and alternate spellings; do not penalize case or punctuation.
- Missing the key term itself is "again" even if surrounding detail is right.
- A long response time relative to a short answer suggests effortful recall:
  prefer "hard" over "good" when the answer is right but was slow.
"""

CONCEPTUAL_RUBRIC = """Rubric (conceptual / long-form):
- Grade the content, NOT the prose quality, grammar, or structure.
- Reward correct reasoning and coverage of the key points even when the
  phrasing and ordering differ completely from the reference answer.
- Partial credit is expected: list every idea the user got right in
  matched_points and every one they omitted in missed_points, since the user
  sees those lists and they carry more weight than the grade for this profile.
- "good" = the substantive points are present; "hard" = the core idea is
  there but a material part is missing or muddled.
"""

MATH_CODE_RUBRIC = """Rubric (math / code):
- Treat the reference answer as ONE worked solution, not a string to match.
- Check two things separately: (a) is the final result correct, (b) is the
  method valid. A correct result reached by an invalid method is "hard".
- Accept different-but-equivalent notation, variable names, algebraic forms,
  and any algorithm with the same complexity and output.
- Do not penalize omitted intermediate steps if the result is right.
- If you cannot verify equivalence with confidence, say so in reasoning and
  lower your confidence value rather than guessing a grade.
"""

PROFILES: dict[str, str] = {
    "short_answer": SHORT_ANSWER_RUBRIC,
    "conceptual": CONCEPTUAL_RUBRIC,
    "math_code": MATH_CODE_RUBRIC,
}

DEFAULT_PROFILE = "short_answer"
# §4.2: math/code always escalates — hardest category for a 4B-class model.
ALWAYS_ESCALATE = {"math_code"}


def build_prompt(
    profile: str,
    *,
    front: str,
    back: str,
    user_answer: str,
    latency_ms: int,
    card_type: str,
) -> str:
    rubric = PROFILES.get(profile, PROFILES[DEFAULT_PROFILE])
    return BASE_PROMPT.format(
        front=front,
        back=back,
        user_answer=user_answer,
        latency_ms=latency_ms,
        card_type=card_type,
        rubric=rubric,
    )


CARD_GEN_PROMPT = """You are helping build spaced-repetition flashcards from a passage
the user is reading. Produce at most {max_cards} cards that test the most
important, self-contained facts in the passage. Prefer cloze deletions for
definitions and enumerations, Q&A for causal or conceptual material.

Passage:
\"\"\"{passage}\"\"\"

Respond with ONLY a JSON object, no prose and no code fences:
{{"cards": [{{"kind": "cloze|qa", "front": "...", "back": "...",
  "cloze_text": "text with {{{{c1::deletions}}}} — only when kind is cloze"}}]}}
"""

LEECH_PROMPT = """A spaced-repetition card keeps being failed by the user. Diagnose why
and propose ONE remediation.

Card front: {front}
Card back: {back}
Times failed: {lapses}
The user's recent failed answers:
{failed_answers}

Choose exactly one:
- "rewrite": the card is answerable but poorly worded — supply a clearer version.
- "split": the card tests too much at once — supply 2-4 smaller cards.
- "ambiguous": the card is ambiguous or miswritten and needs the user's judgement.

Respond with ONLY a JSON object, no prose and no code fences:
{{"kind": "rewrite|split|ambiguous", "rationale": "one or two sentences",
  "cards": [{{"front": "...", "back": "..."}}]}}
For "ambiguous", return an empty cards list.
"""
