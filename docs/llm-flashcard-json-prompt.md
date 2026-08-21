# LLM prompt: generate a card JSON file (with Learn & Practice)

Paste the block below into any LLM chat (ChatGPT, Claude, Gemini, ...) along
with your source material, then import the JSON it returns via
**Decks → Import JSON**, or `POST /api/import/json?deck=<name>`.

---

## Prompt

```
You are generating flashcards for a spaced-repetition app. The user types a
full answer from memory (not multiple choice), so cards must have one clear,
checkable answer — not vague or multi-part.

Output ONLY a JSON array, no prose before or after. Each element is one card:

Basic (question/answer):
{
  "front": "<question, one fact>",
  "back": "<the answer>",
  "quote": "<1-4 sentence excerpt from the source that states this fact>",
  "locator": "<section/heading/page this came from, if known>",
  "source_title": "<title of the source material>",
  "tags": ["<topic>"]
}

Cloze (fill-in-the-blank, for terms/definitions embedded in a sentence):
{
  "kind": "cloze",
  "cloze_text": "<sentence with the key term wrapped like {{c1::term}}>",
  "back": "<extra context shown after grading, optional>",
  "quote": "<1-4 sentence excerpt from the source this sentence is drawn from>",
  "locator": "<section/heading/page>",
  "source_title": "<title of the source material>",
  "tags": ["<topic>"]
}

Rules:
- One card = one atomic fact. Split compound facts into separate cards.
- "front"/"cloze_text" must be answerable without seeing "back" first.
- "quote" is REQUIRED on every card. It's what the app teaches from before
  quizzing (Learn & Practice) — write it as a short, self-contained
  explanation of the fact, not just the bare answer restated. If you're
  working from a source document, quote it directly; if you're writing from
  general knowledge, write 1-4 sentences that would teach a newcomer the
  concept.
- "locator" and "source_title" are optional but cheap — include them
  whenever you know where the fact came from.
- Keep "front"/"back"/"cloze_text" under ~500 characters; "quote" under
  ~800 characters.
- Use {{c1::x}}, {{c2::y}} for multiple deletions in one cloze sentence only
  when the deletions are genuinely linked; otherwise make separate cards.
- Do not invent facts. If the source doesn't support a fact, drop the card.

Generate cards from the material below:

<PASTE YOUR SOURCE TEXT / NOTES / TOPIC HERE>
```

---

## Example output

```json
[
  {
    "front": "What replaces profit maximization during a balance sheet recession?",
    "back": "Debt minimization.",
    "quote": "During such a recession the private sector shifts from profit maximization to debt minimization, prioritizing paying down debt and repairing balance sheets.",
    "locator": "The Behavioral Shift",
    "source_title": "Balance Sheet Recessions",
    "tags": ["macro"]
  },
  {
    "kind": "cloze",
    "cloze_text": "The {{c1::mitochondrion}} is the powerhouse of the cell.",
    "back": "Produces ATP via oxidative phosphorylation.",
    "quote": "Mitochondria generate most of the cell's supply of ATP, used as a source of chemical energy.",
    "locator": "Ch. 4",
    "source_title": "Cell Biology 101",
    "tags": ["biology"]
  }
]
```

## Importing

- **App:** Decks → Import JSON → paste the array → enter a deck name → Import.
- **API:** `POST /api/import/json?deck=<name>` with the array as the body
  (or wrap it: `{"deck": "...", "notes": [...]}`).

## Notes on the "quote" field

- Any card with a non-empty `quote` gets a citation attached, which is what
  unlocks the "Learn & Practice" reading step before the question.
- Cards with no `quote` still import fine — they just skip straight to being
  quizzed, same as any hand-made card.
- Unlike cards generated from an uploaded document, a JSON-imported quote
  isn't checked against a separate source file — it's taken as given. Bad
  input here means a bad lesson, not a rejected import, so review the LLM's
  output before importing at scale.
