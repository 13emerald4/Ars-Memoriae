"""LLM grading subsystem (§4) — a local Ollama model.

Every call goes to the Ollama daemon at OLLAMA_BASE_URL; no API key is
involved and nothing leaves the machine.

1. JSON output is requested (Ollama's ``format: "json"``) but still parsed
   tolerantly, since models wrap JSON in prose or code fences. The rubric
   templates in grading_profiles.py end with an explicit JSON contract, so a
   loosely formatted reply still parses.
2. Every outbound call is wrapped so an unreachable daemon, a model that
   isn't pulled, or a malformed response raises ``GradingUnavailable``, which
   the router turns into ``degraded_to_manual`` (§4.3) rather than a 500.
3. The model scores correctness 0-100 rather than picking a grade directly —
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


class VramExhaustedError(GradingUnavailable):
    """Raised when the local Ollama model ran out of GPU VRAM or host memory."""

    def __init__(
        self,
        message: str,
        failed_model: str,
        fallback_model: str | None = None,
        available_models: list[str] | None = None,
    ):
        super().__init__(message)
        self.failed_model = failed_model
        self.fallback_model = fallback_model
        self.available_models = available_models or []


def is_memory_or_vram_error(exc: Exception | str) -> bool:
    """Detects whether an Ollama error is caused by VRAM or host memory exhaustion."""
    text = str(exc).lower()
    return any(
        phrase in text
        for phrase in (
            "cudamalloc failed",
            "out of memory",
            "unable to allocate",
            "memory layout cannot be allocated",
            "cuda0 buffer",
            "cpu buffer",
            "exit status 2",
            "exit status 1",
            "panic: unable to load model",
            "exit status -1073741819",
        )
    )


ALLOWED_QWEN_CODER_SIZES: tuple[str, ...] = ("7b", "3b", "1.5b")


def is_allowed_qwen_coder_model(model_name: str | None) -> bool:
    """Returns True only for quantized Qwen 2.5 Coder models in 7B, 3B, or 1.5B sizes."""
    if not model_name:
        return False
    m = model_name.lower().strip()
    # Must be in the Qwen 2.5 Coder family
    if "qwen2.5-coder" not in m:
        return False
    # Never allow embeddings or rerankers
    if "embed" in m or "rerank" in m:
        return False
    # Must match one of the permitted sizes (7b, 3b, 1.5b)
    for size in ALLOWED_QWEN_CODER_SIZES:
        pattern = rf"(^|[:\-_]){re.escape(size)}([:\-_]|$)"
        if re.search(pattern, m):
            return True
    return False


def resolve_model(model_name: str | None) -> str:
    """The requested model if it is on the allowlist, else the default."""
    if model_name and is_allowed_qwen_coder_model(model_name):
        return model_name
    return settings.default_grading_model


async def find_local_fallback_models(
    base_url: str,
    current_model: str,
) -> tuple[str | None, list[str]]:
    """Returns (next_biggest_model, all_smaller_models) from installed local Ollama models.
    Strictly restricted to allowed quantized Qwen 2.5 Coder models (7B, 3B, 1.5B).
    """
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(f"{base_url}/api/tags")
            if resp.status_code != 200:
                return None, []
            data = resp.json()
            models = data.get("models", [])
    except Exception as exc:
        log.warning("Could not query Ollama tags: %s", exc)
        return None, []

    installed: list[dict[str, Any]] = []
    for m in models:
        name = m.get("name", "")
        if not is_allowed_qwen_coder_model(name):
            continue
        size = m.get("size", 0)
        installed.append({"name": name, "size": size})

    # Sort descending by size (e.g. 7B -> 3B -> 1.5B)
    installed.sort(key=lambda x: x["size"], reverse=True)

    current_size = None
    for m in installed:
        if m["name"] == current_model:
            current_size = m["size"]
            break

    smaller: list[str] = []
    for m in installed:
        if m["name"] == current_model:
            continue
        if (current_size is not None and m["size"] < current_size) or (current_size is None and m["name"] != current_model):
            smaller.append(m["name"])

    if not smaller:
        return None, []

    next_biggest = smaller[0]
    return next_biggest, smaller


class GradingService:
    def __init__(
        self,
        model: str | None = None,
        escalation_model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.model = resolve_model(model)
        self.escalation_model = escalation_model or settings.escalation_grading_model
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.last_used_model: str | None = None

    # ── transport ───────────────────────────────────────────────────────────

    async def _generate_ollama(
        self,
        prompt: str,
        model: str,
        schema: dict | None = None,
        **kwargs: Any,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                # Ollama silently drops the *start* of an over-long prompt —
                # the instructions — so this must fit the longest prompt.
                "num_ctx": settings.ollama_num_ctx,
                # Greedy decoding on every call: Ollama's default temperature
                # samples, so the same answer could get a different grade.
                "temperature": 0,
            },
        }
        if schema is not None or kwargs.get("response_schema") is not None:
            payload["format"] = "json"

        last_exc = None
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=45.0) as client:
                    resp = await client.post(
                        f"{self.base_url}/api/generate",
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    self.last_used_model = model
                    return data.get("response", "")
            except httpx.ConnectError as exc:
                raise GradingUnavailable(
                    f"Could not connect to Ollama at {self.base_url}. Make sure Ollama is running (`ollama run {model}`)."
                ) from exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    raise GradingUnavailable(
                        f"Model '{model}' not found in Ollama. Run: ollama pull {model}"
                    ) from exc
                last_exc = exc
                await asyncio.sleep(0.5 * (attempt + 1))
            except Exception as exc:
                last_exc = exc
                await asyncio.sleep(0.5 * (attempt + 1))

        if last_exc:
            raise GradingUnavailable(f"Ollama generation failed: {last_exc}") from last_exc
        return ""

    async def _generate(
        self,
        prompt: str,
        model: str | None = None,
        schema: dict | None = None,
        thinking_budget: int | None = None,
        allow_smaller_model: bool = False,
        **kwargs: Any,
    ) -> str:
        target_model = resolve_model(model or self.model)
        self.last_used_model = target_model
        try:
            return await self._generate_ollama(
                prompt,
                model=target_model,
                schema=schema or kwargs.get("response_schema"),
                **kwargs,
            )
        except Exception as exc:
            # Check if this failure is caused by VRAM or host memory exhaustion
            if is_memory_or_vram_error(exc):
                next_model, smaller_models = await find_local_fallback_models(self.base_url, target_model)
                log.warning(
                    "Ollama model '%s' hit VRAM/memory limit (%s). Fallback model: %s, all smaller: %s",
                    target_model,
                    exc,
                    next_model,
                    smaller_models,
                )
                if allow_smaller_model and next_model:
                    log.info("Auto-falling back to next biggest local model: %s", next_model)
                    self.last_used_model = next_model
                    return await self._generate_ollama(
                        prompt,
                        model=next_model,
                        schema=schema or kwargs.get("response_schema"),
                        **kwargs,
                    )
                else:
                    raise VramExhaustedError(
                        message=f"Local model '{target_model}' ran out of GPU VRAM / host memory: {exc}",
                        failed_model=target_model,
                        fallback_model=next_model,
                        available_models=smaller_models,
                    ) from exc
            raise

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
        allow_smaller_model: bool = False,
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
        target_model = model or self.model
        if allow_smaller_model:
            raw = await self._generate(prompt, target_model, SCORE_SCHEMA, allow_smaller_model=True)
        else:
            raw = await self._generate(prompt, target_model, SCORE_SCHEMA)
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
        model: str | None = None,
        allow_smaller_model: bool = False,
        force_escalate: bool = False,
    ) -> dict:
        """§4.2 escalation: a disputed card or a math/code profile goes straight
        to the escalation model; a low-confidence grade is retried on it.

        A no-op when the escalation model is the grading model (the default),
        since asking the same model twice buys nothing. If the escalation model
        isn't pulled, the grading model's answer is kept rather than lost.
        """
        primary_model = model or self.model

        async def grade_on(m: str) -> dict:
            result = await self.grade(
                front,
                back,
                user_answer,
                profile,
                card_type,
                test_code=test_code,
                previous_weaknesses=previous_weaknesses,
                model=m,
                allow_smaller_model=allow_smaller_model,
            )
            result["model_used"] = self.last_used_model or m
            result["escalated"] = m != primary_model
            return result

        can_escalate = self.escalation_model != primary_model
        if can_escalate and (force_escalate or profile in ALWAYS_ESCALATE):
            try:
                return await grade_on(self.escalation_model)
            except GradingUnavailable:
                pass  # fall through to the grading model

        result = await grade_on(primary_model)
        if can_escalate and result["confidence"] < settings.grading_confidence_threshold:
            try:
                return await grade_on(self.escalation_model)
            except GradingUnavailable:
                return result  # keep the low-confidence answer over nothing
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
        out = [_normalize_generated_card(c) for c in cards[:max_cards] if isinstance(c, dict)]
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
            item = _normalize_generated_card(c)
            quote = str(c.get("quote", "")).strip()
            item["quote"] = quote
            item["quote_verified"] = quote_is_grounded(quote, passage)
            item["locator"] = locator
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
                models = [
                    m.get("name", "")
                    for m in data.get("models", [])
                    if m.get("name") and is_allowed_qwen_coder_model(m.get("name"))
                ]
                return sorted(models)
            except Exception as exc:
                raise GradingUnavailable(
                    f"Could not connect to Ollama at {self.base_url} ({exc}). Is Ollama running?"
                ) from exc


# ── parsing & sanity checks ─────────────────────────────────────────────────


def _normalize_generated_card(c: dict) -> dict:
    """One model-proposed card, coerced to the shape the accept endpoints take."""
    is_cloze = c.get("kind") == "cloze" and bool(c.get("cloze_text"))
    is_code = c.get("kind") == "code" or bool(c.get("starter_code")) or bool(c.get("starter_tests"))
    item = {
        "kind": "cloze" if is_cloze else ("code" if is_code else "qa"),
        "front": str(c.get("front", "")).strip(),
        "back": str(c.get("back", "")).strip(),
        "cloze_text": str(c.get("cloze_text", "")).strip() or None,
    }
    if is_code:
        item["title"] = c.get("title")
        item["starter_code"] = c.get("starter_code")
        item["starter_tests"] = c.get("starter_tests")
        item["test_cases"] = c.get("test_cases") or []
    return item


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
