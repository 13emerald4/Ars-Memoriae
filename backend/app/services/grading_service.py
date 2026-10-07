"""LLM grading subsystem (§4) — BYOK Gemini/Gemma.

Four deviations from the §4.6 sketch, all forced by how the API — or FSRS —
actually behaves rather than by preference:

1. Gemma models served through the Gemini API do not accept
   ``response_schema``/``response_mime_type`` (that is a Gemini-model feature)
   and reject ``system_instruction``. So structured output is *attempted* and
   falls back to prompt-instructed JSON + tolerant parsing. The rubric
   templates in grading_profiles.py already end with an explicit JSON contract
   so the fallback path is not a downgrade in practice.
2. ``grade_with_escalation`` does not mutate ``self.model`` — the sketch's
   version would leave the instance permanently escalated for every later card.
   The escalation model is passed per call instead.
3. Every outbound call is wrapped so a missing key, a quota error, or a
   malformed response raises ``GradingUnavailable``, which the router turns
   into ``degraded_to_manual`` (§4.3) rather than a 500.
4. The model scores correctness 0-100 rather than picking a grade directly —
   that's the actual feedback the user sees and the LLM reasons about. The
   4-point grade FSRS schedules on is derived from the score
   (``grade_for_score``); it can't be scored away, since py-fsrs's
   stability/difficulty transitions are only defined per discrete rating.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

import httpx

from app.core.config import settings
from app.services.document_service import quote_is_grounded
from app.services.grading_profiles import (
    ALWAYS_ESCALATE,
    CARD_GEN_PROMPT,
    DOC_CARD_GEN_PROMPT,
    LEECH_PROMPT,
    LESSON_PROMPT,
    SOCRATIC_LINE_HINT_PROMPT,
    SOCRATIC_PROMPT,
    WEAKNESS_HINT_PROMPT,
    build_prompt,
)

log = logging.getLogger(__name__)

SCORE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "score": {"type": "NUMBER"},
        "confidence": {"type": "NUMBER"},
        "matched_points": {"type": "ARRAY", "items": {"type": "STRING"}},
        "missed_points": {"type": "ARRAY", "items": {"type": "STRING"}},
        "overlooked_phrases": {"type": "ARRAY", "items": {"type": "STRING"}},
        "weaknesses": {"type": "ARRAY", "items": {"type": "STRING"}},
        "improvements": {"type": "ARRAY", "items": {"type": "STRING"}},
        "persistent_weaknesses": {"type": "ARRAY", "items": {"type": "STRING"}},
        "reasoning": {"type": "STRING"},
    },
    "required": ["score", "confidence", "reasoning"],
}

GRADES = ("again", "hard", "good", "easy")
# High to low so the first band a score clears wins; below all of these is
# "again". These mirror the scale described to the model in BASE_PROMPT.
SCORE_BANDS: tuple[tuple[float, str], ...] = ((90, "easy"), (70, "good"), (40, "hard"))
# Score points per grade step of accumulated calibration bias (apply_bias).
# Bands are 30-40 points wide, so 20 moves a mid-band score into the next one
# without letting a modest bias leapfrog two grades.
BIAS_SCORE_STEP = 20.0
# §Socratic AI Guide: how much of the reference answer's content words a
# guide message can echo before it counts as leaking the answer rather than
# hinting at it. The same overlap heuristic §4.3 uses to sanity-check grades.
SOCRATIC_LEAK_THRESHOLD = 0.75
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "in", "is", "it",
    "of", "on", "or", "that", "the", "to", "was", "were", "with",
}


class GradingUnavailable(RuntimeError):
    """Raised when grading cannot complete; callers degrade to manual (§4.3)."""


class GradingService:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        escalation_model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key
        # Normalize legacy cloud models (Gemini / Gemma) to local Qwen 2.5 Coder
        target_model = model or settings.default_grading_model
        if target_model.startswith("gemini") or target_model.startswith("gemma"):
            target_model = settings.default_grading_model
        self.model = target_model
        self.escalation_model = escalation_model or settings.escalation_grading_model
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")

    # ── transport ───────────────────────────────────────────────────────────

    async def _generate(
        self,
        prompt: str,
        model: str | None = None,
        schema: dict | None = None,
        thinking_budget: int | None = None,
        **kwargs: Any,
    ) -> str:
        target_model = model or self.model
        if target_model.startswith("gemini") or target_model.startswith("gemma"):
            target_model = settings.default_grading_model
        payload: dict[str, Any] = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
        }
        if schema is not None or kwargs.get("response_schema") is not None:
            payload["format"] = "json"

        last_exc = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=90.0) as client:
                    resp = await client.post(
                        f"{self.base_url}/api/generate",
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return data.get("response", "")
            except httpx.ConnectError as exc:
                raise GradingUnavailable(
                    f"Could not connect to Ollama at {self.base_url}. Make sure Ollama is running (`ollama run {target_model}`)."
                ) from exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    raise GradingUnavailable(
                        f"Model '{target_model}' not found in Ollama. Run: ollama pull {target_model}"
                    ) from exc
                last_exc = exc
                await asyncio.sleep(1.0 * (attempt + 1))
            except Exception as exc:
                last_exc = exc
                await asyncio.sleep(1.0 * (attempt + 1))

        if last_exc:
            raise GradingUnavailable(f"Ollama generation failed: {last_exc}") from last_exc
        return ""

    # ── grading (§4.1) ──────────────────────────────────────────────────────

    async def grade(
        self,
        front: str,
        back: str,
        user_answer: str,
        profile: str = "short_answer",
        card_type: str = "basic",
        test_code: str | None = None,
        previous_weaknesses: list[str] | None = None,
        model: str | None = None,
    ) -> dict:
        prompt = build_prompt(
            profile,
            front=front,
            back=back,
            user_answer=user_answer,
            card_type=card_type,
            test_code=test_code,
            previous_weaknesses=previous_weaknesses,
        )
        raw = await self._generate(prompt, model or self.model, SCORE_SCHEMA)
        return _normalize_result(parse_json(raw))

    async def grade_with_escalation(
        self,
        front: str,
        back: str,
        user_answer: str,
        profile: str = "short_answer",
        card_type: str = "basic",
        test_code: str | None = None,
        previous_weaknesses: list[str] | None = None,
        force_escalate: bool = False,
    ) -> dict:
        """Evaluates answers directly using Qwen 2.5 Coder 7B."""
        target_model = self.model
        result = await self.grade(
            front,
            back,
            user_answer,
            profile,
            card_type,
            test_code=test_code,
            previous_weaknesses=previous_weaknesses,
            model=target_model,
        )
        result["model_used"] = target_model
        result["escalated"] = False
        return result

    # ── IR card generation (§8.3) — reuses this same client ─────────────────

    async def generate_cards(
        self,
        passage: str,
        max_cards: int = 5,
        model: str | None = None,
        thinking_budget: int | None = None,
    ) -> list[dict]:
        raw = await self._generate(
            CARD_GEN_PROMPT.format(passage=passage[:8000], max_cards=max_cards),
            model or self.model,
            thinking_budget=thinking_budget,
        )
        data = parse_json(raw)
        cards = data.get("cards") if isinstance(data, dict) else None
        if not isinstance(cards, list):
            raise GradingUnavailable("card generation returned no cards")
        out = []
        for c in cards[:max_cards]:
            if not isinstance(c, dict):
                continue
            is_cloze = c.get("kind") == "cloze" and bool(c.get("cloze_text"))
            is_code = c.get("kind") == "code" or bool(c.get("starter_code")) or bool(c.get("starter_tests"))
            kind = "cloze" if is_cloze else ("code" if is_code else "qa")
            item = {
                "kind": kind,
                "front": str(c.get("front", "")).strip(),
                "back": str(c.get("back", "")).strip(),
                "cloze_text": str(c.get("cloze_text", "")).strip() or None,
            }
            if is_code:
                item["title"] = c.get("title")
                item["starter_code"] = c.get("starter_code")
                item["starter_tests"] = c.get("starter_tests")
                item["test_cases"] = c.get("test_cases") or []
            out.append(item)
        return [c for c in out if c["front"] or c["cloze_text"]]

    async def generate_cards_with_citations(
        self,
        passage: str,
        locator: str,
        max_cards: int = 5,
        model: str | None = None,
        thinking_budget: int | None = None,
    ) -> list[dict]:
        """Cards from a document passage, each carrying the span it came from.

        The quote is *checked* against the passage rather than trusted: a
        citation the reader can't find in the source is worse than none, so an
        ungrounded quote is kept but flagged, and the UI falls back to showing
        the real passage instead of a sentence the model may have invented.
        """
        raw = await self._generate(
            DOC_CARD_GEN_PROMPT.format(
                passage=passage[:8000], max_cards=max_cards, locator=locator or "this document"
            ),
            model or self.model,
            thinking_budget=thinking_budget,
        )
        data = parse_json(raw)
        cards = data.get("cards") if isinstance(data, dict) else None
        if not isinstance(cards, list):
            raise GradingUnavailable("card generation returned no cards")

        out = []
        for c in cards[:max_cards]:
            if not isinstance(c, dict):
                continue
            is_cloze = c.get("kind") == "cloze" and bool(c.get("cloze_text"))
            is_code = c.get("kind") == "code" or bool(c.get("starter_code")) or bool(c.get("starter_tests"))
            kind = "cloze" if is_cloze else ("code" if is_code else "qa")
            quote = str(c.get("quote", "")).strip()
            item = {
                "kind": kind,
                "front": str(c.get("front", "")).strip(),
                "back": str(c.get("back", "")).strip(),
                "cloze_text": str(c.get("cloze_text", "")).strip() or None,
                "quote": quote,
                "quote_verified": quote_is_grounded(quote, passage),
                "locator": locator,
            }
            if is_code:
                item["title"] = c.get("title")
                item["starter_code"] = c.get("starter_code")
                item["starter_tests"] = c.get("starter_tests")
                item["test_cases"] = c.get("test_cases") or []
            out.append(item)
        return [c for c in out if c["front"] or c["cloze_text"]]

    # ── Learn & Practice lessons ────────────────────────────────────────────

    async def generate_lesson(
        self,
        front: str,
        back: str,
        passages: list[str],
        max_words: int = 160,
        model: str | None = None,
    ) -> dict:
        """A short lesson teaching the idea a card tests, from its citations.

        Grounded the same way card generation is: the passages are the only
        permitted source. Teaching material that quietly invents an
        explanation is worse than none, because the user has no reason to
        doubt it — they are reading it precisely because they don't know the
        material yet.
        """
        if not passages:
            raise GradingUnavailable("no source passages to teach from")
        joined = "\n\n---\n\n".join(p.strip() for p in passages if p and p.strip())[:8000]
        raw = await self._generate(
            LESSON_PROMPT.format(
                front=front, back=back, passages=joined, max_words=max_words
            ),
            model or self.model,
        )
        data = parse_json(raw)
        lesson = str(data.get("lesson", "")).strip() if isinstance(data, dict) else ""
        if not lesson:
            raise GradingUnavailable("lesson generation returned nothing")
        points = data.get("key_points") or []
        return {
            "lesson": lesson,
            "key_points": [str(p).strip() for p in points if str(p).strip()][:6],
        }

    # ── Socratic AI Guide & Targeted Weakness Hint ───────────────────────────

    async def generate_weakness_hint(
        self,
        front: str,
        back: str,
        active_weaknesses: list[str],
        model: str | None = None,
    ) -> dict:
        """Generates a targeted diagnostic hint based on prior recorded weaknesses."""
        if not active_weaknesses:
            return {
                "hint": "No prior weaknesses recorded for this card. Focus on recalling the core principles and key definitions.",
                "has_past_weaknesses": False,
            }

        weaknesses_text = "\n".join(f"- {w}" for w in active_weaknesses[:8])
        raw = await self._generate(
            WEAKNESS_HINT_PROMPT.format(
                front=front,
                back=back,
                weaknesses_text=weaknesses_text,
            ),
            model or self.model,
            schema={"type": "OBJECT", "properties": {"hint": {"type": "STRING"}}, "required": ["hint"]},
        )
        data = parse_json(raw)
        hint = str(data.get("hint", "")).strip() if isinstance(data, dict) else ""
        if not hint:
            hint = f"Focus on avoiding your past stumbling blocks: {', '.join(active_weaknesses[:2])}."

        if leaks_reference_answer(back, hint):
            log.warning("weakness hint leaked reference answer; substituting generic reminder")
            hint = f"Keep in mind your previous difficulty with: {active_weaknesses[0]}."

        return {
            "hint": hint,
            "has_past_weaknesses": True,
        }

    async def ask_socratic_question(
        self,
        front: str,
        back: str,
        history: list[tuple[str, str]],
        latest: str,
        active_weaknesses: list[str] | None = None,
        model: str | None = None,
    ) -> dict:
        """One turn of Socratic hinting: a diagnostic question, never the answer.

        The prompt is the first line of defense — instructed never to reveal
        ``back`` — but prompts are not guarantees, so the reply is also
        checked the same way §4.3 cross-checks a grade: if it echoes most of
        the reference answer's content words, it's swapped for a generic
        nudge rather than trusted and shown.
        """
        weakness_intro = ""
        if active_weaknesses:
            weakness_intro = (
                f"[Tutor note: The student had previous difficulty on this card with: "
                f"{'; '.join(active_weaknesses[:4])}]\n"
            )

        convo = "\n".join(
            f"{'Guide' if role == 'guide' else 'Student'}: {text}" for role, text in history[-12:]
        )
        full_convo = f"{weakness_intro}{convo}" if weakness_intro else convo
        raw = await self._generate(
            SOCRATIC_PROMPT.format(
                front=front,
                back=back,
                history=full_convo or "(none yet)",
                latest=latest.strip() or "(the student hasn't replied yet — ask an opening question)",
            ),
            model or self.model,
        )
        data = parse_json(raw)
        message = str(data.get("message", "")).strip() if isinstance(data, dict) else ""
        if not message:
            raise GradingUnavailable("guide returned no message")

        if leaks_reference_answer(back, message):
            log.warning("socratic guide reply echoed the reference answer; substituting a nudge")
            message = "Let's hold off on the full answer — what part of it are you already sure of?"

        return {"message": message, "on_track": bool(isinstance(data, dict) and data.get("on_track"))}

    async def ask_socratic_line_hint(
        self,
        front: str,
        back: str,
        code: str,
        line_number: int,
        language: str = "typescript",
        model: str | None = None,
    ) -> dict:
        """Generates a targeted Socratic hint for a specific line of code in the IDE.

        Grounded in the canonical reference solution (``back``) and the student's
        preceding code, without ever leaking the actual line or solution verbatim.
        """
        lines = code.split("\n")
        total_lines = len(lines)
        clamped_line = max(1, min(line_number, max(1, total_lines)))

        current_line_text = lines[clamped_line - 1] if clamped_line <= total_lines else ""
        code_before = "\n".join(lines[: clamped_line - 1]) or "(no preceding code)"

        code_with_lines = "\n".join(
            f"{'--> ' if i + 1 == clamped_line else '    '}{i + 1}: {line}"
            for i, line in enumerate(lines)
        )

        raw = await self._generate(
            SOCRATIC_LINE_HINT_PROMPT.format(
                front=front,
                back=back,
                code_with_lines=code_with_lines,
                line_number=clamped_line,
                current_line_text=current_line_text or "(empty / cursor here)",
                code_before=code_before,
            ),
            model or self.model,
        )
        data = parse_json(raw)
        hint = str(data.get("hint", "")).strip() if isinstance(data, dict) else ""
        target_concept = str(data.get("target_concept", "")).strip() if isinstance(data, dict) else None

        if not hint:
            raise GradingUnavailable("Guide returned no hint for this line")

        def _leaks_code_line(reference_solution: str, text: str) -> bool:
            if leaks_reference_answer(reference_solution, text):
                return True
            for ref_line in reference_solution.split("\n"):
                stripped_line = ref_line.strip()
                if len(stripped_line) >= 6 and stripped_line in text:
                    return True
            return False

        if _leaks_code_line(back, hint):
            log.warning("Socratic line hint echoed reference answer code; substituting a pedagogical nudge")
            hint = f"Focus on line {clamped_line}: consider what operation or state change connects your previous setup to the expected return type."

        return {
            "hint": hint,
            "target_concept": target_concept,
            "line_number": clamped_line,
            "current_line_text": current_line_text,
        }

    # ── leech remediation (§3.2) ────────────────────────────────────────────

    async def suggest_leech_remediation(
        self, front: str, back: str, lapses: int, failed_answers: list[str]
    ) -> dict:
        answers = "\n".join(f"- {a}" for a in failed_answers[:8]) or "- (none recorded)"
        raw = await self._generate(
            LEECH_PROMPT.format(front=front, back=back, lapses=lapses, failed_answers=answers),
            self.escalation_model,
        )
        data = parse_json(raw)
        kind = data.get("kind") if isinstance(data, dict) else None
        if kind not in ("rewrite", "split", "ambiguous"):
            kind = "ambiguous"
        cards = data.get("cards") if isinstance(data, dict) else []
        return {
            "kind": kind,
            "rationale": str(data.get("rationale", "")).strip() if isinstance(data, dict) else "",
            "cards": [c for c in (cards or []) if isinstance(c, dict)],
        }

    async def decompose_card_atomicity(self, front: str, back: str) -> list[dict[str, str]]:
        """Decomposes a complex, non-atomic card into 2-4 atomic question-answer pairs."""
        prompt = (
            "You are a cognitive science and spaced repetition expert specializing in the "
            "Minimum Information Principle (SuperMemo Rule 4).\n"
            "The user has a flashcard that is too complex, lengthy, or tests multiple facts at once.\n"
            "Deconstruct it into 2 to 4 simple, concise, and atomic flashcards. Each card must test exactly "
            "ONE fact with a clear, concise question and a short, direct answer (under 15 words).\n\n"
            f"Original Card Prompt:\n{front}\n\n"
            f"Original Card Answer:\n{back}\n\n"
            "Output JSON with a 'cards' array of objects with 'front' and 'back' fields."
        )
        schema = {
            "type": "OBJECT",
            "properties": {
                "cards": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "front": {"type": "STRING"},
                            "back": {"type": "STRING"},
                        },
                        "required": ["front", "back"],
                    },
                }
            },
            "required": ["cards"],
        }
        raw = await self._generate(prompt, self.model, response_schema=schema)
        data = parse_json(raw)
        cards = data.get("cards") if isinstance(data, dict) else []
        out = []
        for c in cards:
            if isinstance(c, dict) and c.get("front") and c.get("back"):
                out.append({"front": str(c["front"]).strip(), "back": str(c["back"]).strip()})
        return out

    async def verify_engine(self) -> list[str]:
        """Confirm Ollama daemon is reachable and list downloaded models."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                return sorted(models)
            except Exception as exc:
                raise GradingUnavailable(
                    f"Could not connect to Ollama at {self.base_url} ({exc}). Is Ollama running?"
                ) from exc

    async def verify_key(self) -> list[str]:
        return await self.verify_engine()


# ── parsing & sanity checks ─────────────────────────────────────────────────


def parse_json(raw: str) -> dict:
    """Tolerant JSON extraction — models wrap output in prose or code fences
    when structured output isn't enforced by the schema path."""
    if not raw:
        raise GradingUnavailable("empty response")
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    raise GradingUnavailable("unparseable grading response")


def grade_for_score(score: float) -> str:
    """Bucket a 0-100 correctness score into the 4-point scale FSRS's
    scheduling math is defined over (§4.1). The score is what the user sees
    and what grading reasons about; FSRS still needs one of Again/Hard/Good/
    Easy, since stability/difficulty transitions are only defined per rating —
    that's py-fsrs's API, not a choice this app can route around.
    """
    for threshold, grade in SCORE_BANDS:
        if score >= threshold:
            return grade
    return "again"


def parse_score(raw) -> int:
    """A 0-100 integer from whatever shape the model returned it in.

    Rounded to an integer *before* bucketing, because the UI renders the score
    rounded: a raw 89.6 displayed as "90%" while bucketed as "good" (70-89)
    would contradict the band the user is reading. One integer decides both.

    A trailing "%" is tolerated — models write "85%" often enough that letting
    it collapse the whole grading call into the manual fallback would be a
    silly way to lose an otherwise good response.
    """
    if isinstance(raw, str):
        raw = raw.strip().rstrip("%").strip()
    try:
        score = float(raw)
    except (TypeError, ValueError):
        raise GradingUnavailable(f"invalid score {raw!r}") from None
    return round(min(max(score, 0.0), 100.0))


def _normalize_result(data: dict) -> dict:
    if "score" not in data:
        raise GradingUnavailable("response missing score")
    score = parse_score(data["score"])
    try:
        confidence = float(data.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    return {
        "score": score,
        "grade": grade_for_score(score),
        "confidence": min(max(confidence, 0.0), 1.0),
        "matched_points": [str(x).strip() for x in (data.get("matched_points") or []) if str(x).strip()][:12],
        "missed_points": [str(x).strip() for x in (data.get("missed_points") or []) if str(x).strip()][:12],
        "overlooked_phrases": [str(x).strip() for x in (data.get("overlooked_phrases") or []) if str(x).strip()][:12],
        "weaknesses": [str(x).strip() for x in (data.get("weaknesses") or []) if str(x).strip()][:12],
        "improvements": [str(x).strip() for x in (data.get("improvements") or []) if str(x).strip()][:12],
        "persistent_weaknesses": [str(x).strip() for x in (data.get("persistent_weaknesses") or []) if str(x).strip()][:12],
        "reasoning": str(data.get("reasoning", "")).strip(),
    }


def _is_schema_unsupported(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(
        s in msg
        for s in ("response_schema", "responseschema", "response_mime_type", "json mode",
                  "not supported", "unsupported", "system_instruction")
    )


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOPWORDS and len(w) > 2}


def heuristic_overlap(reference: str, answer: str) -> float:
    """Cheap keyword-overlap check that runs alongside the LLM call (§4.3):
    the fraction of the reference answer's content words the user reproduced."""
    ref, ans = _tokens(reference), _tokens(answer)
    if not ref:
        return 1.0 if ans else 0.0
    return len(ref & ans) / len(ref)


def leaks_reference_answer(back: str, message: str) -> bool:
    """Whether a Socratic Guide message gives the reference answer away.

    Two checks, because neither alone covers the range of answers:

    **Verbatim containment** is what catches short answers. ``_tokens`` drops
    anything under three characters, so a reference of "4" or "pH" reduces to
    an *empty* token set — and ``heuristic_overlap`` reports an empty
    reference as a perfect 1.0 match. That is the right call when grading a
    user's answer (nothing to miss means nothing was missed) and exactly
    backwards here, where it condemned every message on such a card. Matched
    on word boundaries so "4" doesn't fire on "40" and "pH" doesn't fire on
    "phase".

    **Token overlap** then catches the longer case the containment check
    can't: a multi-word answer restated in the model's own words.
    """
    ref = back.strip()
    if not ref:
        return False

    pattern = re.escape(ref)
    if ref[:1].isalnum():
        pattern = r"\b" + pattern
    if ref[-1:].isalnum():
        pattern = pattern + r"\b"
    if re.search(pattern, message, re.I):
        return True

    # No comparable tokens (a short or purely symbolic answer) means the
    # containment check above was the whole test — an empty-reference overlap
    # score would only ever produce a false positive.
    if not _tokens(ref):
        return False
    return heuristic_overlap(ref, message) > SOCRATIC_LEAK_THRESHOLD


def disagrees_with_heuristic(grade: str, overlap: float) -> bool:
    """True when heuristic and LLM diverge enough to ask the user (§4.3).

    Only the two unambiguous directions are flagged: the model called it right
    while the answer shares almost nothing with the reference, or it called it
    wrong while the answer reproduced nearly all of it.
    """
    if grade in ("good", "easy") and overlap < 0.15:
        return True
    return bool(grade == "again" and overlap > 0.8)


def apply_bias(score: int, bias: float) -> int:
    """Per-user calibration (§4.3): nudge the *score* by the running average of
    the user's own overrides instead of fine-tuning anything.

    This adjusts the score rather than the grade so the two can never
    contradict each other. Nudging the grade alone produced visible nonsense:
    a score of 85 shown next to a suggested "easy", while the Easy button in
    front of the user is labelled 90-100%.

    Bias is accumulated in grade steps (see confirm_review), so it is scaled
    into score points here. The step is wide enough that a full one-grade bias
    reliably carries a mid-band score into the neighbouring band, which is what
    a one-grade correction is asking for.
    """
    return round(min(max(score + bias * BIAS_SCORE_STEP, 0.0), 100.0))
