"""Builds the comprehensive Socratic lessons module for all 105 cards in the JS/TS course."""

import json
import re

from app.content.js_ts_course import COURSE
from app.content.js_ts_course.model import CodeCard, CompileCard, PredictCard


def clean_sentences(text: str) -> list[str]:
    # Split text into clean sentences
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 10]

lessons = {}

for part in COURSE:
    for sub in part.subdecks:
        for card in sub.cards:
            key = card.key
            subdeck_name = sub.name
            why = card.why.strip()
            sentences = clean_sentences(why)

            # Construct Socratic Lesson based on card kind and content
            if isinstance(card, CodeCard):
                title = card.title
                task = card.task
                lang = "TypeScript" if card.language == "typescript" else "JavaScript"

                body = (
                    f"When implementing `{title}` in {lang}, what core invariants must you satisfy?\n\n"
                    f"{task}\n\n"
                    f"Consider how {lang} handles type boundaries and evaluation order. "
                    f"Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\n"
                    f"{why}"
                )

                points = []
                for s in sentences:
                    points.append(s)
                if not points:
                    points.append(f"Satisfy the core contract for `{title}` without violating boundary conditions.")
                points.append("Check edge cases (empty inputs, null/undefined, unexpected types) gracefully.")

            elif isinstance(card, PredictCard):
                prompt = card.prompt or "What does this print?"
                lang = "TypeScript" if card.language == "typescript" else "JavaScript"

                body = (
                    f"Before predicting the runtime outcome, trace execution step-by-step through the {lang} engine:\n\n"
                    f"Ask yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? "
                    f"Where might intuition differ from the ECMAScript specification?\n\n"
                    f"{why}"
                )

                points = []
                for s in sentences:
                    points.append(s)
                if not points:
                    points.append("Trace runtime evaluation step-by-step.")
                points.append("Verify language evaluation order and object identity rather than assumptions.")

            elif isinstance(card, CompileCard):
                body = (
                    f"When the TypeScript compiler checks this code under `--strict`, what safety invariants does it verify?\n\n"
                    f"Examine each statement through the eyes of the type checker: Does the compiler have enough information to guarantee soundness? "
                    f"Ask yourself: Where does a potential type hole or unproven contract trigger a compile diagnostic?\n\n"
                    f"{why}"
                )

                points = []
                for s in sentences:
                    points.append(s)
                if not points:
                    points.append("Ensure every variable is strictly narrowed before accessing properties.")
                points.append("Under strict mode, unverified indexing or missing cases produce compile errors.")

            # Keep between 2 and 4 key points
            final_points = [p for p in points if p][:4]

            lessons[key] = {
                "body": body,
                "key_points": final_points
            }

print(f"Generated {len(lessons)} lessons.")

# Write to backend/app/content/js_ts_course/lessons.py
with open("backend/app/content/js_ts_course/lessons.py", "w", encoding="utf-8") as f:
    f.write('"""Concise Socratic lessons and key points for all 105 course cards.\n\n')
    f.write('Used in Learn & Practice priming to teach mental models before testing.\n"""\n\n')
    f.write('LESSONS: dict[str, dict] = ' + json.dumps(lessons, indent=4) + '\n\n')
    f.write('def get_socratic_lesson(card_key: str) -> tuple[str, list[str]]:\n')
    f.write('    data = LESSONS.get(card_key)\n')
    f.write('    if data:\n')
    f.write('        return data["body"], data["key_points"]\n')
    f.write('    return "", []\n')

print("Wrote backend/app/content/js_ts_course/lessons.py successfully.")
