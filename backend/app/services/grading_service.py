"""LLM grading subsystem (§4) — BYOK Gemini/Gemma.

Three deviations from the §4.6 sketch, all forced by how the API actually
behaves rather than by preference:

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
"""

from __future__ import annotations

import asyncio
import json
import logging
import re

from app.core.config import settings
from app.services.grading_profiles import (
    ALWAYS_ESCALATE,
    CARD_GEN_PROMPT,
    LEECH_PROMPT,
    build_prompt,
)

log = logging.getLogger(__name__)

GRADE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "grade": {"type": "STRING", "enum": ["again", "hard", "good", "easy"]},
        "confidence": {"type": "NUMBER"},
        "matched_points": {"type": "ARRAY", "items": {"type": "STRING"}},
        "missed_points": {"type": "ARRAY", "items": {"type": "STRING"}},
        "reasoning": {"type": "STRING"},
    },
    "required": ["grade", "confidence", "reasoning"],
}

GRADES = ("again", "hard", "good", "easy")
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "in", "is", "it",
    "of", "on", "or", "that", "the", "to", "was", "were", "with",
}


class GradingUnavailable(RuntimeError):
    """Raised when grading cannot complete; callers degrade to manual (§4.3)."""


class GradingService:
    def __init__(
        self,
        api_key: str | None,
        model: str | None = None,
        escalation_model: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model or settings.default_grading_model
        self.escalation_model = escalation_model or settings.escalation_grading_model
        self._client = None

    # ── transport ───────────────────────────────────────────────────────────

    def _get_client(self):
        if not self.api_key:
            raise GradingUnavailable("no_api_key")
        if self._client is None:
            try:
                from google import genai
            except ImportError as exc:  # pragma: no cover - dependency guard
                raise GradingUnavailable("google-genai not installed") from exc
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def _generate(self, prompt: str, model: str, schema: dict | None = None) -> str:
        from google.genai import types

        client = self._get_client()

        async def _call(use_schema: bool) -> str:
            config = None
            if use_schema and schema is not None:
                config = types.GenerateContentConfig(
                    response_mime_type="application/json", response_schema=schema
                )
            resp = await client.aio.models.generate_content(
                model=model, contents=prompt, config=config
            )
            return resp.text or ""

        try:
            return await _call(use_schema=schema is not None)
        except Exception as exc:
            if schema is not None and _is_schema_unsupported(exc):
                log.info("model %s rejected response_schema; retrying unconstrained", model)
                try:
                    return await _call(use_schema=False)
                except Exception as exc2:
                    raise GradingUnavailable(str(exc2)) from exc2
            raise GradingUnavailable(str(exc)) from exc

    # ── grading (§4.1) ──────────────────────────────────────────────────────

    async def grade(
        self,
        front: str,
        back: str,
        user_answer: str,
        latency_ms: int,
        profile: str = "short_answer",
        card_type: str = "basic",
        model: str | None = None,
    ) -> dict:
        prompt = build_prompt(
            profile,
            front=front,
            back=back,
            user_answer=user_answer,
            latency_ms=latency_ms,
            card_type=card_type,
        )
        raw = await self._generate(prompt, model or self.model, GRADE_SCHEMA)
        return _normalize_grade(parse_json(raw))

    async def grade_with_escalation(
        self,
        front: str,
        back: str,
        user_answer: str,
        latency_ms: int,
        profile: str = "short_answer",
        card_type: str = "basic",
        force_escalate: bool = False,
    ) -> dict:
        """§4.2 escalation path: low confidence, a disputed card, or a
        math/code profile retries on the larger model before giving up."""
        escalate_first = force_escalate or profile in ALWAYS_ESCALATE
        first_model = self.escalation_model if escalate_first else self.model
        result = await self.grade(
            front, back, user_answer, latency_ms, profile, card_type, model=first_model
        )
        result["model_used"] = first_model
        result["escalated"] = escalate_first

        if not escalate_first and result["confidence"] < settings.grading_confidence_threshold:
            try:
                retry = await self.grade(
                    front, back, user_answer, latency_ms, profile, card_type,
                    model=self.escalation_model,
                )
            except GradingUnavailable:
                return result  # keep the low-confidence answer over nothing
            retry["model_used"] = self.escalation_model
            retry["escalated"] = True
            return retry
        return result

    # ── IR card generation (§8.3) — reuses this same client ─────────────────

    async def generate_cards(self, passage: str, max_cards: int = 5) -> list[dict]:
        raw = await self._generate(
            CARD_GEN_PROMPT.format(passage=passage[:8000], max_cards=max_cards), self.model
        )
        data = parse_json(raw)
        cards = data.get("cards") if isinstance(data, dict) else None
        if not isinstance(cards, list):
            raise GradingUnavailable("card generation returned no cards")
        out = []
        for c in cards[:max_cards]:
            if not isinstance(c, dict):
                continue
            kind = "cloze" if c.get("kind") == "cloze" and c.get("cloze_text") else "qa"
            out.append(
                {
                    "kind": kind,
                    "front": str(c.get("front", "")).strip(),
                    "back": str(c.get("back", "")).strip(),
                    "cloze_text": str(c.get("cloze_text", "")).strip() or None,
                }
            )
        return [c for c in out if c["front"] or c["cloze_text"]]

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

    async def verify_key(self) -> list[str]:
        """Confirm a pasted key works and report the models it can reach, so
        Settings can show real IDs rather than trusting our configured default."""
        client = self._get_client()

        def _list() -> list[str]:
            names = []
            for m in client.models.list():
                actions = getattr(m, "supported_actions", None) or []
                if not actions or "generateContent" in actions:
                    names.append((m.name or "").removeprefix("models/"))
            return sorted(n for n in names if n)

        try:
            return await asyncio.to_thread(_list)
        except Exception as exc:
            raise GradingUnavailable(str(exc)) from exc


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


def _normalize_grade(data: dict) -> dict:
    grade = str(data.get("grade", "")).strip().lower()
    if grade not in GRADES:
        raise GradingUnavailable(f"invalid grade {grade!r}")
    try:
        confidence = float(data.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    return {
        "grade": grade,
        "confidence": min(max(confidence, 0.0), 1.0),
        "matched_points": [str(x) for x in (data.get("matched_points") or [])][:12],
        "missed_points": [str(x) for x in (data.get("missed_points") or [])][:12],
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


def disagrees_with_heuristic(grade: str, overlap: float) -> bool:
    """True when heuristic and LLM diverge enough to ask the user (§4.3).

    Only the two unambiguous directions are flagged: the model called it right
    while the answer shares almost nothing with the reference, or it called it
    wrong while the answer reproduced nearly all of it.
    """
    if grade in ("good", "easy") and overlap < 0.15:
        return True
    return bool(grade == "again" and overlap > 0.8)


def apply_bias(grade: str, bias: float) -> str:
    """Per-user calibration (§4.3): nudge the grade by the running average of
    the user's own overrides instead of fine-tuning anything."""
    if abs(bias) < 0.5:
        return grade
    idx = GRADES.index(grade)
    return GRADES[min(max(idx + round(bias), 0), len(GRADES) - 1)]
