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
Card type: {card_type}

Score the answer's correctness from 0 to 100, based ONLY on whether the key
concepts it depends on are present and whether its keywords (or clear
synonyms/paraphrases of them) are matched. You are not given how long the
user took to respond, and must not guess at or factor in response speed,
confidence of phrasing, or hedging language — score the substance only.

Use this scale as a guide:
- 0-39: wrong, or missing the key concept entirely
- 40-69: the key concept is present but with a notable error or omission
- 70-89: correct with at most a minor omission
- 90-100: correct and complete

{rubric}

Respond with ONLY a JSON object of this shape, no prose and no code fences:
{{"score": 0-100, "confidence": 0.0-1.0,
  "matched_points": ["..."], "missed_points": ["..."], "reasoning": "one or two sentences"}}
"""

SHORT_ANSWER_RUBRIC = """Rubric (short answer / vocabulary):
- Reward an exact match or a close paraphrase of the key term equally — both
  score the same.
- Accept synonyms and alternate spellings; do not penalize case or punctuation.
- Score by keyword/concept coverage: the key term (or an unambiguous synonym
  of it) being present is what makes an answer score well, regardless of how
  it is phrased around that term.
- Missing the key term itself scores below 40 even if surrounding detail is right.
"""

CONCEPTUAL_RUBRIC = """Rubric (conceptual / long-form):
- Score the content, NOT the prose quality, grammar, or structure.
- Reward correct reasoning and coverage of the key points even when the
  phrasing and ordering differ completely from the reference answer.
- Partial credit is expected: list every idea the user got right in
  matched_points and every one they omitted in missed_points, since the user
  sees those lists and they carry more weight than the score for this profile.
  Let the score track the fraction of key points actually covered.
- 70-89 = the substantive points are present; 40-69 = the core idea is there
  but a material part is missing or muddled.
"""

MATH_CODE_RUBRIC = """Rubric (math / code):
- Treat the reference answer as ONE worked solution, not a string to match.
- Check two things separately: (a) is the final result correct, (b) is the
  method valid. A correct result reached by an invalid method scores 40-69.
- Accept different-but-equivalent notation, variable names, algebraic forms,
  and any algorithm with the same complexity and output.
- Do not penalize omitted intermediate steps if the result is right.
- If you cannot verify equivalence with confidence, say so in reasoning and
  lower your confidence value rather than guessing a score.
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
    card_type: str,
) -> str:
    rubric = PROFILES.get(profile, PROFILES[DEFAULT_PROFILE])
    return BASE_PROMPT.format(
        front=front,
        back=back,
        user_answer=user_answer,
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

DOC_CARD_GEN_PROMPT = """You are building spaced-repetition flashcards from one passage of a
document the user is studying. Produce at most {max_cards} cards testing the most
important, self-contained facts in THIS passage. Prefer cloze deletions for
definitions and enumerations, Q&A for causal or conceptual material.

Every card must also carry a "quote": the shortest span of the passage that
contains the answer, COPIED VERBATIM from the text below. Do not paraphrase,
summarise, correct, or join separated sentences in the quote — it is checked
against the passage character by character and silently dropped if it does not
appear there. If no span of the passage supports a card, do not emit that card.

Use only what this passage states. Do not add outside knowledge.

Passage (from {locator}):
\"\"\"{passage}\"\"\"

Respond with ONLY a JSON object, no prose and no code fences:
{{"cards": [{{"kind": "cloze|qa", "front": "...", "back": "...",
  "cloze_text": "text with {{{{c1::deletions}}}} — only when kind is cloze",
  "quote": "verbatim span from the passage"}}]}}
"""

LESSON_PROMPT = """You are teaching one idea to a student who is about to be tested on it.

Write a short lesson — at most {max_words} words — that gives them what they need to
answer the question below, using ONLY the source passage(s) provided. Do not add
outside facts, figures, definitions or examples that are not in the passages. If the
passages do not fully explain something, say so plainly rather than filling the gap.

Teach the underlying idea — what it means, and why it holds — rather than only
asserting the answer. Do include the answer: the student reads this first and is
then asked to recall it, so withholding it would defeat the exercise.

Write plainly, in the second person, with no heading and no preamble.

The question they will face: {front}
The expected answer: {back}

Source passage(s):
{passages}

Respond with ONLY a JSON object, no prose and no code fences:
{{"lesson": "2-4 short paragraphs of plain text",
  "key_points": ["3-5 short takeaways, each one line"]}}
"""

SOCRATIC_PROMPT = """You are a Socratic tutor helping a student who is stuck on a
flashcard. Your ONLY tool is asking ONE short diagnostic question at a time. You must
NEVER state, paraphrase, spell out, or strongly imply the reference answer — not in this
turn, not in any later one, no matter what the student says or asks. If the student
directly asks for the answer, refuse gently and ask a question instead that narrows in
on the specific gap in their reasoning.

Card front: {front}
Reference answer (never reveal this — your job is to make it unnecessary to say it): {back}

Conversation so far (Guide asks, Student replies):
{history}

The student's latest message: {latest}

Ask exactly one short diagnostic question that points them toward the piece of the
reference answer they seem to be missing, based on everything said so far. If their
latest reply already shows they understand it, say so briefly and encourage them to
commit to typing their real answer now — still without stating the reference answer
yourself.

Respond with ONLY a JSON object, no prose and no code fences:
{{"message": "one short question or encouragement, 1-3 sentences", "on_track": true|false}}
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
