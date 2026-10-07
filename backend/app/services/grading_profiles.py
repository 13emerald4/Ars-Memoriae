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
{previous_weaknesses_section}
Respond with ONLY a JSON object of this shape, no prose and no code fences:
{{"score": 0-100, "confidence": 0.0-1.0,
  "matched_points": ["..."], "missed_points": ["..."], "overlooked_phrases": ["exact phrases from reference answer omitted"],
  "weaknesses": ["specific conceptual, syntactic, or algorithmic flaws in this answer"],
  "improvements": ["weaknesses from previous attempts that the user successfully resolved in this answer"],
  "persistent_weaknesses": ["weaknesses from previous attempts that the user still struggled with or omitted in this answer"],
  "reasoning": "one or two sentences"}}
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

MATH_CODE_RUBRIC = """Rubric (math / code / TDD):
- Treat the reference answer as ONE worked solution or algorithmic implementation, not a strict string match.
- Check two things separately: (a) is the logic/code correct, (b) is the method and complexity optimal. A correct brute-force solution where an optimal algorithm exists scores 50-70.
- Accept different-but-equivalent variable names, helper data structures, language idioms, and alternative algorithms with comparable or better asymptotic complexity.
- Specific algorithmic evaluation:
  * Time & Space Complexity: Verify whether the user's implementation matches optimal complexity (e.g. O(n) vs O(n^2)). Note any complexity shortfalls in missed_points.
  * Overlooked Edge Cases: Check boundary conditions (empty input, single element, negative numbers, duplicates, large bounds). State any unhandled edge cases in missed_points and overlooked_phrases.
  * Omitted Concepts: List missing helper logic, base cases, or invariant checks in overlooked_phrases.
- Unit Testing / TDD Evaluation:
  * When a user provides unit tests alongside their implementation, evaluate both parts:
    - Implementation (50%): Correct logic and edge case handling.
    - Test Suite (50%): Boundary value coverage (testing right at threshold boundaries), partition coverage, and independent assertions. Award matched_points for thorough tests and list missing boundary tests in missed_points.
- Partial credit: Award matched_points for correct core data structures, state transitions, loop invariants, base conditions, and well-designed test cases.
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
    test_code: str | None = None,
    previous_weaknesses: list[str] | None = None,
) -> str:
    rubric = PROFILES.get(profile, PROFILES[DEFAULT_PROFILE])
    submission = user_answer
    if test_code and test_code.strip():
        submission = f"Implementation Code:\n{user_answer}\n\nAuthored Unit Test Suite:\n{test_code}"

    if previous_weaknesses:
        formatted_prev = "\n".join(f"- {w}" for w in previous_weaknesses)
        previous_weaknesses_section = (
            f"\nPrevious recorded weaknesses the user struggled with on earlier reviews of this card:\n"
            f"{formatted_prev}\n"
            f"Compare this attempt with those previous weaknesses:\n"
            f"- If the user resolved/corrected any previous weakness, list it in 'improvements'.\n"
            f"- If the user still failed or omitted any previous weakness, list it in 'persistent_weaknesses'.\n"
            f"- In 'weaknesses', list any flaws (new or recurring) present in this current answer.\n"
        )
    else:
        previous_weaknesses_section = (
            "\nIn 'weaknesses', list any specific conceptual, syntactic, or algorithmic flaws present in this answer (or an empty list if none).\n"
            "Set 'improvements' to [] and 'persistent_weaknesses' to [] since there are no previous recorded weaknesses.\n"
        )
    return BASE_PROMPT.format(
        front=front,
        back=back,
        user_answer=submission,
        card_type=card_type,
        rubric=rubric,
        previous_weaknesses_section=previous_weaknesses_section,
    )


WEAKNESS_HINT_PROMPT = """You are a cognitive coach helping a student review a flashcard they previously struggled with.
Your goal is to offer a targeted diagnostic hint based on their past mistakes.
You must NEVER reveal, recite, or give away the reference answer.

Card question: {front}
Reference answer (NEVER state this): {back}

Student's past recorded weaknesses on this card:
{weaknesses_text}

Provide ONE concise diagnostic hint (1-2 sentences) reminding them to watch out for their specific prior pitfalls or directing their attention to the concept they previously missed.
Respond with ONLY a JSON object, no prose and no code fences:
{{"hint": "one or two sentence diagnostic hint without giving away the solution"}}
"""


CARD_GEN_PROMPT = """You are helping build spaced-repetition flashcards from a passage
the user is reading. Produce at most {max_cards} cards testing the most
important, self-contained facts, mechanisms, and specifications in the passage.

Card Type Guidelines:
1. Prefer cloze deletions for definitions, core syntax, and enumerations.
2. Use Q&A for causal mechanisms, conceptual principles, or test-suite design:
   - For software testing / specs: Ask the user to identify equivalence classes, boundary thresholds, or test assertions.
   - Formulate "back" with clear, precise terminology and core conceptual components so an automated grader can accurately detect recalled versus overlooked points.
3. For programming challenges or function specifications, emit "kind": "code":
   - "title": Short problem title
   - "front": Function specification and test requirements
   - "starter_code": Type and function signature. For Result, use CPSC 210 convention: type Result<T, E = string> = {{ ok: true; value: T }} | {{ ok: false; error: E }};
   - "starter_tests": Starter unit test suite template using CPSC 210 conventions:
     * test("description", checkExpect(() => actual, expected))
     * test("description", checkError(() => ...))
     * assertOk(r) and assertErr(r)
     * For async: checkExpect(async () => await f(...), expected)
   - "back": Complete reference solution
   - "test_cases": [ {{"input": {{ ... }}, "expected": ...}} ]

Passage:
\"\"\"{passage}\"\"\"

Respond with ONLY a JSON object, no prose and no code fences:
{{"cards": [{{"kind": "cloze|qa|code", "title": "...", "front": "...", "back": "...",
  "cloze_text": "text with {{{{c1::deletions}}}} — only when kind is cloze",
  "starter_code": "optional starter code — only when kind is code",
  "starter_tests": "optional unit tests — only when kind is code",
  "test_cases": [{{"input": {{}}, "expected": "..."}}]}}]}}
"""

DOC_CARD_GEN_PROMPT = """You are building spaced-repetition flashcards from one passage of a
document the user is studying. Produce at most {max_cards} cards testing the most
important, self-contained facts, mechanisms, and specifications in THIS passage.

Card Type Guidelines:
1. Prefer cloze deletions for definitions and enumerations, Q&A for conceptual material and test boundary analysis.
2. For programming challenges, emit "kind": "code" with:
   - "starter_code" (use type Result<T, E = string> = {{ ok: true; value: T }} | {{ ok: false; error: E }} for Result)
   - "starter_tests" (using test("...", checkExpect(() => actual, expected)), test("...", checkError(() => ...)), assertOk, assertErr)
   - "test_cases"
3. Every card must also carry a "quote": the shortest span of the passage that
contains the answer, COPIED VERBATIM from the text below. Do not paraphrase,
summarise, correct, or join separated sentences in the quote — it is checked
against the passage character by character and silently dropped if it does not
appear there. If no span of the passage supports a card, do not emit that card.

Use only what this passage states. Do not add outside knowledge.

Passage (from {locator}):
\"\"\"{passage}\"\"\"

Respond with ONLY a JSON object, no prose and no code fences:
{{"cards": [{{"kind": "cloze|qa|code", "title": "...", "front": "...", "back": "...",
  "cloze_text": "text with {{{{c1::deletions}}}} — only when kind is cloze",
  "starter_code": "optional starter code — only when kind is code",
  "starter_tests": "optional unit tests — only when kind is code",
  "test_cases": [{{"input": {{}}, "expected": "..."}}],
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

SOCRATIC_LINE_HINT_PROMPT = """You are an expert Socratic Code Tutor and Computer Science Instructor.
A student is in an interactive IDE solving a coding problem and is stuck on a specific line of code.
They have requested a Socratic hint for the line they are currently writing.

Problem Title & Specification:
{front}

Canonical Reference Solution (for the tutor's reference ONLY — NEVER reveal this code verbatim):
```
{back}
```

Student's Code with Line Markers:
```
{code_with_lines}
```

The Student is Currently Focused on Line {line_number}:
Current text on line {line_number}: `{current_line_text}`

Preceding Relevant Code Written by Student:
```
{code_before}
```

Instructions for the Socratic Hint:
1. Examine what the canonical reference solution does at this corresponding stage or step of the algorithm.
2. Review what the student has already implemented in previous lines ({code_before}).
3. Formulate a targeted, pedagogically sound Socratic hint focused squarely on what line {line_number} needs to achieve:
   - Connect their previous code to this step (e.g. how to use variables, parameters, or data structures already declared).
   - Point them toward the logic, expression, condition, or invariant needed on this line.
   - Mention the relevant concept or purpose (e.g. accumulator initialization, loop termination, edge-case check).
4. ABSOLUTE RULE: You must NEVER provide the completed line of code or spoil the exact syntax verbatim. Guide them so THEY write the code.
5. Keep the hint concise (2 to 4 sentences maximum), encouraging, and clear.

Respond with ONLY a JSON object, no prose and no code fences:
{{"hint": "Your Socratic guiding question and hint for this line", "target_concept": "Short 2-4 word concept name"}}
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
