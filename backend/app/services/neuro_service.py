"""Neuroscience Cognitive Synthesis Service (§Neuroscience).

Implements:
1. Dynamic Prompt Mutation (Reconsolidation Invariant Generalization)
2. Mnemonic Vignette Synthesis (Dual-Coding & Von Restorff Bizarreness Effect)
3. Pre-Test Hypothesis & Prediction Error Evaluation (Dopaminergic RPE)
4. Contrastive Minimal-Pair Drills (Dentate Gyrus Pattern Separation)
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Card, Deck, Note, SisterPair, User
from app.services.grading_service import GradingService
from app.services.rendering import render

log = logging.getLogger(__name__)


def sanitize_for_prompt(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"```", "'''", str(text).strip())


# ── 1. Dynamic Prompt Mutation ────────────────────────────────────────────────


MUTATION_PROMPTS = {
    "counterfactual": (
        "Invert or alter a core assumption or condition of this concept. "
        "Ask what would fail, how the behavior would break, or what consequence follows if that condition did not hold."
    ),
    "scenario": (
        "Situate this concept in a realistic, concrete application or edge-case scenario. "
        "Ask how the principle applies under specific constraints."
    ),
    "adversarial": (
        "Adopt an adversarial testing perspective. Ask how an adversary, buggy input, "
        "or race condition could exploit the concept or violate its invariant."
    ),
    "perspective": (
        "Shift perspective (e.g., from client to server, producer to consumer, or caller to callee). "
        "Ask how this concept appears or behaves from the opposite viewpoint."
    ),
}


async def mutate_prompt(
    db: AsyncSession,
    user: User,
    card: Card,
    mutation_type: str = "counterfactual",
) -> tuple[str, str, str | None]:
    """Generates an orthogonal mutation of the card's front prompt.

    Returns: (original_front, mutated_prompt, model_used)
    """
    front, back = render(
        card.note.note_type.template_kind,
        card.note.field_values or {},
        card.template_slot,
    )

    clean_mutation = mutation_type.lower().strip()
    if clean_mutation not in MUTATION_PROMPTS:
        clean_mutation = "counterfactual"

    instruction = MUTATION_PROMPTS[clean_mutation]
    service = GradingService.for_user(user)

    sys_prompt = (
        "You are a cognitive neuroscience tutor specializing in memory reconsolidation "
        "and invariant generalization. Your goal is to test whether the learner understands "
        "the deep conceptual invariant, rather than memorizing surface wording."
    )

    user_prompt = f"""Card Prompt (Front):
{sanitize_for_prompt(front)}

Reference Fact (Back):
{sanitize_for_prompt(back)}

Task:
{instruction}

Guidelines:
1. Write a single, concise variant question (1-2 sentences).
2. DO NOT reveal the reference answer or give away the solution in the question.
3. Test the exact same core concept from this new angle.
4. Output JSON in this exact format:
{{"variant_question": "Your question here..."}}"""

    from app.services.grading_service import GradingUnavailable

    try:
        raw = await service._call_ollama(sys_prompt, user_prompt)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise ValueError("LLM response missing JSON object")
        parsed = json.loads(match.group(0))
        variant = str(parsed.get("variant_question", "")).strip()
        if not variant:
            raise ValueError("LLM returned empty variant_question")
        return front, variant, service.last_used_model or service.model
    except GradingUnavailable:
        raise
    except Exception as exc:
        raise GradingUnavailable(f"Prompt mutation failed on '{service.model}': {exc}") from exc


# ── 2. Mnemonic Vignette Synthesizer (Von Restorff / Dual Coding) ───────────────


async def generate_mnemonic_vignette(
    db: AsyncSession,
    user: User,
    card: Card,
) -> tuple[str, str | None]:
    """Generates a vivid, bizarre 2-sentence visual narrative for a memory palace locus.

    Returns: (vignette_text, model_used)
    """
    from app.services.grading_service import GradingUnavailable

    front, back = render(
        card.note.note_type.template_kind,
        card.note.field_values or {},
        card.template_slot,
    )
    locus = card.spatial_locus or "a grand memory palace pedestal"

    service = GradingService.for_user(user)
    sys_prompt = (
        "You are an ancient Roman memory grandmaster (Ars Memoriae) combined with a cognitive neuroscientist. "
        "You craft memorable mental imagery exploiting Dual Coding Theory and the Von Restorff (Bizarreness) Effect."
    )

    user_prompt = f"""Concept:
Front: {sanitize_for_prompt(front)}
Back: {sanitize_for_prompt(back)}
Target Memory Palace Locus: {sanitize_for_prompt(locus)}

Instructions:
1. Synthesize an absurd, highly sensory, 2-sentence visual vignette anchoring this concept at the designated locus.
2. Involve dynamic physical motion, vivid colors, exaggerated size, or unusual interactions that directly symbolize the key concept.
3. Keep it under 45 words.
4. Output JSON:
{{"vignette": "Your 2-sentence bizarre scene here..."}}"""

    try:
        raw = await service._call_ollama(sys_prompt, user_prompt)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise ValueError("LLM response missing JSON object")
        parsed = json.loads(match.group(0))
        vignette = str(parsed.get("vignette", "")).strip()
        if not vignette:
            raise ValueError("LLM returned empty vignette")
        card.mnemonic_vignette = vignette
        await db.commit()
        return vignette, service.last_used_model or service.model
    except GradingUnavailable:
        raise
    except Exception as exc:
        raise GradingUnavailable(f"Mnemonic synthesis failed on '{service.model}': {exc}") from exc


# ── 3. Pre-Test Hypothesis & Prediction Error Evaluation ─────────────────────


async def evaluate_pretest_prediction(
    db: AsyncSession,
    user: User,
    card: Card,
    prediction: str,
    confidence: int,
) -> dict[str, Any]:
    """Compares pre-test hypothesis with reference answer and checks for prediction error."""
    from app.services.grading_service import GradingUnavailable

    front, back = render(
        card.note.note_type.template_kind,
        card.note.field_values or {},
        card.template_slot,
    )

    service = GradingService.for_user(user)
    sys_prompt = (
        "You are an expert tutor evaluating a learner's pre-test hypothesis. "
        "They attempted to predict the answer before studying it."
    )
    user_prompt = f"""Question:
{sanitize_for_prompt(front)}

Reference Truth:
{sanitize_for_prompt(back)}

Learner's Pre-Test Hypothesis:
{sanitize_for_prompt(prediction)}

Confidence Level: {confidence}/4

Evaluate:
1. Is the hypothesis accurate, partially correct, or a misconception?
2. Provide a 2-sentence educational reconciliation highlighting the exact difference between their intuition and reality.
Output JSON:
{{"is_accurate": true/false, "feedback": "Your 2-sentence feedback..."}}"""

    try:
        raw = await service._call_ollama(sys_prompt, user_prompt)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise ValueError("LLM response missing JSON object")
        parsed = json.loads(match.group(0))
        is_accurate = bool(parsed.get("is_accurate", False))
        feedback = str(parsed.get("feedback", "")).strip()
        if not feedback:
            raise ValueError("LLM returned empty feedback")
    except GradingUnavailable:
        raise
    except Exception as exc:
        raise GradingUnavailable(f"Pre-test prediction evaluation failed on '{service.model}': {exc}") from exc

    # High-confidence error: learner was certain (confidence >= 3 or 4) but incorrect
    high_confidence_error = (not is_accurate) and (confidence >= 3)

    return {
        "card_id": str(card.id),
        "prediction": prediction,
        "reference_answer": back,
        "confidence": confidence,
        "is_accurate": is_accurate,
        "feedback": feedback,
        "high_confidence_error": high_confidence_error,
    }


# ── 4. Contrastive Minimal-Pair Drills (Pattern Separation) ───────────────────


async def generate_contrast_drill(
    db: AsyncSession,
    user: User,
    pair: SisterPair,
) -> dict[str, Any]:
    """Constructs a side-by-side discriminative comparison drill between confusable notes."""
    from app.services.grading_service import GradingUnavailable

    cards_a = (await db.scalars(select(Card).where(Card.note_id == pair.note_a_id))).all()
    cards_b = (await db.scalars(select(Card).where(Card.note_id == pair.note_b_id))).all()

    card_a = cards_a[0] if cards_a else None
    card_b = cards_b[0] if cards_b else None

    if not card_a or not card_b:
        raise ValueError("Cards for this sister pair could not be found")

    front_a, back_a = render(card_a.note.note_type.template_kind, card_a.note.field_values or {}, card_a.template_slot)
    front_b, back_b = render(card_b.note.note_type.template_kind, card_b.note.field_values or {}, card_b.template_slot)

    title_a = " ".join(front_a.split())[:50]
    title_b = " ".join(front_b.split())[:50]

    service = GradingService.for_user(user)
    sys_prompt = (
        "You are a cognitive neuroscientist training Dentate Gyrus pattern separation. "
        "Two concepts frequently interfere because they appear superficially similar but require distinct responses."
    )
    user_prompt = f"""Concept A:
Front: {sanitize_for_prompt(front_a)}
Back: {sanitize_for_prompt(back_a)}

Concept B:
Front: {sanitize_for_prompt(front_b)}
Back: {sanitize_for_prompt(back_b)}

Task:
1. Create a discriminative challenge: a single question asking what critical boundary separates A from B.
2. Formulate the single key distinction (1 sentence).
3. Provide 2 divergent condition rows where one applies and the other fails.
Output JSON:
{{
  "discriminative_challenge": "What is the critical boundary condition separating...",
  "key_distinction": "Concept A applies when..., whereas Concept B requires...",
  "divergent_conditions": [
    {{"condition": "Condition 1", "choice_a": "A behavior", "choice_b": "B behavior"}},
    {{"condition": "Condition 2", "choice_a": "A behavior", "choice_b": "B behavior"}}
  ]
}}"""

    try:
        raw = await service._call_ollama(sys_prompt, user_prompt)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise ValueError("LLM response missing JSON object")
        parsed = json.loads(match.group(0))
        return {
            "pair_id": str(pair.id),
            "concept_a_title": title_a,
            "concept_b_title": title_b,
            "front_a": front_a,
            "back_a": back_a,
            "front_b": front_b,
            "back_b": back_b,
            "discriminative_challenge": parsed.get("discriminative_challenge", f"Contrast {title_a} vs {title_b}"),
            "key_distinction": parsed.get("key_distinction", "Pay careful attention to the boundary conditions."),
            "divergent_conditions": parsed.get("divergent_conditions", []),
        }
    except GradingUnavailable:
        raise
    except Exception as exc:
        raise GradingUnavailable(f"Contrast drill generation failed on '{service.model}': {exc}") from exc
