"""Technical lexicon, concordance, and concept definition service.

Uses local Qwen 2.5 Coder via Ollama to generate pedagogical, concise definitions
for unfamiliar terms encountered in cards, lessons, and code drills, with
instant SQLite cache lookup.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import LexiconCache, User
from app.services.grading_service import GradingService, parse_json

log = logging.getLogger(__name__)

LEXICON_SYSTEM_PROMPT = """You are an expert computer science professor and technical concordance tutor.
A student clicked on a term they do not understand: "{term}".
Reading Context: "{context}"

Explain this concept with high pedagogical clarity, concise precision, and zero fluff.
Respond ONLY with a JSON object following this exact structure:
{{
  "definition": "1-2 sentence core definition in plain English explaining what it means fundamentally.",
  "context_explanation": "2-3 sentences explaining how this applies to programming, data structures, or hardware, and why it matters in this context.",
  "example": "A concrete code snippet, numerical example, or real-world illustration (e.g. '0.1 + 0.2 === 0.30000000000000004 in JavaScript/Python').",
  "domain": "The primary domain (e.g. 'Computer Systems / Numerics', 'Algorithms', 'Data Structures', 'Programming Languages').",
  "related_terms": ["3-5 related technical terms or concepts for their concordance"]
}}
"""

CURATED_OFFLINE_DEFINITIONS: dict[str, dict] = {
    "binary approximations": {
        "definition": "The representation of real numbers using a finite sequence of binary bits (base-2), which cannot precisely represent certain base-10 decimal fractions.",
        "context_explanation": "In standard IEEE 754 floating-point numbers (used by JavaScript, Python, TypeScript), fractions like 0.1 cannot be represented with finite binary digits, similar to how 1/3 is repeating in decimal. Performing arithmetic on these values accumulates small rounding errors.",
        "example": "0.1 + 0.2 in Python evaluates to 0.30000000000000004 instead of exactly 0.3.",
        "domain": "Computer Systems / Numerics",
        "related_terms": ["floating-point", "IEEE 754", "rounding errors", "precision", "fixed-point arithmetic"],
    },
    "floating-point": {
        "definition": "A formulaic representation of real numbers as a significand (mantissa) and an exponent, enabling a wide dynamic range within a fixed number of bits.",
        "context_explanation": "Floating-point representation trades exact precision for a huge range of values. Because bits are finite, arithmetic operations may introduce subtle rounding discrepancies.",
        "example": "float64 / double uses 1 sign bit, 11 exponent bits, and 52 fraction bits.",
        "domain": "Computer Systems / Architecture",
        "related_terms": ["IEEE 754", "binary approximations", "mantissa", "overflow", "underflow"],
    },
    "rounding errors": {
        "definition": "The mathematical discrepancy between the exact arithmetic result and the value stored in finite computer memory.",
        "context_explanation": "When numbers with infinite decimal/binary expansions are truncated to fit in computer registers, the discarded digits create rounding errors. Ordering operations (e.g. multiplying before dividing) minimizes error compounding.",
        "example": "(1.0 / 3.0) * 3.0 may yield 0.9999999999999999 instead of 1.0.",
        "domain": "Numerical Computing",
        "related_terms": ["binary approximations", "truncation error", "precision", "numerical stability"],
    },
    "time complexity": {
        "definition": "A theoretical measure of the amount of computational time an algorithm requires as a function of the input size (n).",
        "context_explanation": "Expressed in Big-O notation, it categorizes how runtime scales (e.g. O(1), O(n), O(n log n), O(n^2)), allowing comparison of algorithmic efficiency regardless of hardware.",
        "example": "Binary search has O(log n) time complexity, whereas linear scan has O(n).",
        "domain": "Algorithms & Complexity",
        "related_terms": ["Big-O notation", "space complexity", "asymptotic analysis", "worst-case"],
    },
    "space complexity": {
        "definition": "A measure of the total memory an algorithm uses during its execution relative to the input size.",
        "context_explanation": "Includes both auxiliary space (temporary variables, call stacks) and input space. Efficient algorithms strive to run in O(1) auxiliary space (in-place).",
        "example": "Recursive DFS on a tree has O(h) space complexity on the call stack, where h is tree height.",
        "domain": "Algorithms & Complexity",
        "related_terms": ["auxiliary space", "in-place", "call stack", "memory footprint"],
    },
}


async def lookup_term(
    db: AsyncSession,
    term: str,
    context: str | None = None,
    user: User | None = None,
) -> dict:
    clean_term = term.strip()
    norm_term = clean_term.lower()

    # 1. Check database cache
    cached_entry = (
        await db.execute(
            select(LexiconCache)
            .where(LexiconCache.term_normalized == norm_term)
            .order_by(LexiconCache.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if cached_entry:
        return {
            "term": cached_entry.term_display,
            "definition": cached_entry.definition,
            "context_explanation": cached_entry.context_explanation,
            "example": cached_entry.example,
            "domain": cached_entry.domain,
            "related_terms": cached_entry.related_terms or [],
            "cached": True,
            "model_used": cached_entry.model_used,
            "created_at": cached_entry.created_at,
        }

    # 2. Check curated offline dictionary for instant match
    if norm_term in CURATED_OFFLINE_DEFINITIONS:
        entry = CURATED_OFFLINE_DEFINITIONS[norm_term]
        db_entry = LexiconCache(
            term_normalized=norm_term,
            term_display=clean_term,
            definition=entry["definition"],
            context_explanation=entry["context_explanation"],
            example=entry.get("example"),
            domain=entry.get("domain", "Computer Science"),
            related_terms=entry.get("related_terms", []),
            model_used="curated_lexicon",
        )
        db.add(db_entry)
        await db.commit()
        await db.refresh(db_entry)
        return {
            "term": clean_term,
            "definition": entry["definition"],
            "context_explanation": entry["context_explanation"],
            "example": entry.get("example"),
            "domain": entry.get("domain", "Computer Science"),
            "related_terms": entry.get("related_terms", []),
            "cached": False,
            "model_used": "curated_lexicon",
            "created_at": db_entry.created_at,
        }

    # 3. Query local LLM (Qwen 2.5 Coder via Ollama)
    model_name = user.grading_model if user else settings.default_grading_model
    service = GradingService(model=model_name)
    prompt = LEXICON_SYSTEM_PROMPT.format(
        term=clean_term,
        context=(context or "").strip()[:1000] or "General computer science study context.",
    )

    try:
        raw_response = await service._generate(prompt, model=model_name)
        data = parse_json(raw_response)
        definition = data.get("definition") or f"A technical concept in {clean_term}."
        context_explanation = data.get("context_explanation")
        example = data.get("example")
        domain = data.get("domain", "Computer Science")
        related_terms = data.get("related_terms") or []
        model_used = model_name
    except Exception as exc:
        log.warning("Ollama lexicon lookup failed for '%s': %s; using heuristic fallback", clean_term, exc)
        definition = f"Technical term: {clean_term}. Used in computational logic and programming."
        context_explanation = f"In this passage, '{clean_term}' specifies an essential implementation detail or operational constraint."
        example = None
        domain = "Computer Science"
        related_terms = []
        model_used = "heuristic_fallback"

    # Persist to database cache
    db_entry = LexiconCache(
        term_normalized=norm_term,
        term_display=clean_term,
        definition=definition,
        context_explanation=context_explanation,
        example=example,
        domain=domain,
        related_terms=related_terms,
        model_used=model_used,
    )
    db.add(db_entry)
    await db.commit()
    await db.refresh(db_entry)

    return {
        "term": clean_term,
        "definition": definition,
        "context_explanation": context_explanation,
        "example": example,
        "domain": domain,
        "related_terms": related_terms,
        "cached": False,
        "model_used": model_used,
        "created_at": db_entry.created_at,
    }


async def get_recent_terms(db: AsyncSession, limit: int = 15) -> list[dict]:
    rows = (
        await db.execute(
            select(LexiconCache)
            .order_by(LexiconCache.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()

    # Deduplicate by normalized term preserving most recent
    seen = set()
    out = []
    for r in rows:
        if r.term_normalized in seen:
            continue
        seen.add(r.term_normalized)
        out.append(
            {
                "term": r.term_display,
                "definition": r.definition,
                "domain": r.domain,
                "created_at": r.created_at,
            }
        )
    return out
