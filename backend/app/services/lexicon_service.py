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
from app.models import Card, Deck, LexiconCache, User
from app.services.grading_service import GradingService, parse_json

log = logging.getLogger(__name__)

LEXICON_SYSTEM_PROMPT = """You are an expert educator, terminology specialist, and concordance tutor across diverse academic and professional disciplines (humanities, languages, sciences, history, law, arts, mathematics, and technology).
A student is studying and encountered a term they want to understand: "{term}".
Subject / Deck Context:
\"\"\"{context}\"\"\"

CRITICAL DOMAIN & RELEVANCE RULES:
1. Examine the Subject / Deck Context and the term itself to accurately identify the real academic domain (e.g. Spanish Language, World History, Organic Chemistry, Literature, Philosophy, Medicine, Law, Linguistics, Economics, Mathematics, Computer Science, etc.).
2. If the deck, card, or context has NOTHING to do with programming, software, or computer science:
   - Absolutely DO NOT include any programming, computer science, data structures, hardware, or software analogies!
   - NEVER force an analogy to programming (e.g. NEVER compare human settlements, grammatical terms, historical treaties, or biological cells to Python lists, arrays, functions, classes, or memory registers).
   - "definition": Clear, natural 1-2 sentence core definition of the term in its authentic subject domain.
   - "context_explanation": 2-3 sentences explaining why this concept matters within its real subject domain (e.g. for language: its cultural or grammatical usage; for history: historical significance; for biology: biological role).
   - "example": A realistic, domain-appropriate example (e.g. a sample usage sentence in the target language with English translation, a real historical event, a biological phenomenon, or legal scenario).
   - "domain": The authentic discipline (e.g. 'Spanish Language & Culture', 'Human Geography', 'Microbiology', 'Contract Law').
   - "related_terms": 3-5 terms from that SAME discipline.
3. ONLY if the subject or term is genuinely about programming, software development, or computer science:
   - Provide a technical explanation and a code snippet or algorithmic example.
   - "domain": A relevant computing domain (e.g. 'Algorithms & Data Structures', 'Programming Languages', 'Computer Systems').

Respond ONLY with a JSON object following this exact schema:
{{
  "definition": "1-2 sentence core definition in plain English explaining what it means fundamentally.",
  "context_explanation": "2-3 sentences explaining why it matters in this context without forcing unrelated CS metaphors.",
  "example": "A concrete domain-appropriate example (or null if not applicable).",
  "domain": "The authentic subject domain.",
  "related_terms": ["3-5 related terms within the same domain"]
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
    card_id: str | None = None,
    deck_name: str | None = None,
    thematic_nature: str | None = None,
    user: User | None = None,
) -> dict:
    clean_term = term.strip()
    norm_term = clean_term.lower()

    # Resolve card / deck metadata if card_id provided
    card_content = ""
    if card_id:
        try:
            import uuid
            card_uuid = uuid.UUID(card_id) if isinstance(card_id, str) else card_id
            card = await db.get(Card, card_uuid)
            if card:
                deck = card.deck or (await db.get(Deck, card.deck_id))
                if not deck_name and deck:
                    deck_name = deck.name
                if not thematic_nature:
                    thematic_nature = card.thematic_nature or (deck.thematic_nature if deck else None)
                if not context and card.note and card.note.field_values:
                    card_content = f"Front: {card.note.field_values.get('Front', '')}\nBack: {card.note.field_values.get('Back', '')}"
        except Exception as exc:
            log.debug("Failed resolving card for lexicon lookup %s: %s", card_id, exc)

    # Detect if current deck, term, or context is actually related to Computer Science
    cs_indicators = [
        "programming", "computer science", "software", "coding", "code", "algorithm",
        "algorithms", "data structure", "data structures", "python", "typescript",
        "javascript", "java", "c++", "leetcode", "debugging", "compiler", "cpu",
        "hardware", "operating system", "concurrency", "database", "sql", "git",
        "cpsc", "cs1", "cs2", "cse", "binary", "floating-point"
    ]
    combined_ctx_lower = f"{clean_term} {deck_name or ''} {thematic_nature or ''} {context or ''} {card_content}".lower()
    is_cs_subject = any(ind in combined_ctx_lower for ind in cs_indicators) or norm_term in CURATED_OFFLINE_DEFINITIONS

    # Build pedagogical context
    context_blocks = []
    if deck_name:
        context_blocks.append(f"Deck Name: {deck_name}")
    if thematic_nature:
        context_blocks.append(f"Subject / Thematic Nature: {thematic_nature}")
    if context and context.strip():
        context_blocks.append(f"Context / Reading: {context.strip()[:1000]}")
    elif card_content:
        context_blocks.append(f"Card Content: {card_content[:1000]}")

    full_context_str = "\n".join(context_blocks) if context_blocks else (context or "").strip()[:1000] or "General academic study context."

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
        cached_is_cs = any(
            k in (cached_entry.domain or "").lower()
            for k in ["computer", "programming", "algorithm", "data structure", "software"]
        )
        # Guardrail: If cached entry was forced into Computer Science, but current context is NOT Computer Science, bypass cache!
        if not is_cs_subject and cached_is_cs:
            log.info("Bypassing CS-biased cached lexicon entry for '%s' in non-CS context (%s)", clean_term, deck_name)
        else:
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
        context=full_context_str,
    )

    try:
        raw_response = await service._generate(prompt, model=model_name)
        data = parse_json(raw_response)
        definition = data.get("definition") or f"A key concept: {clean_term}."
        context_explanation = data.get("context_explanation")
        example = data.get("example")
        domain = data.get("domain") or (thematic_nature or deck_name or ("Computer Science" if is_cs_subject else "General Studies"))
        related_terms = data.get("related_terms") or []
        model_used = model_name
    except Exception as exc:
        log.warning("Ollama lexicon lookup failed for '%s': %s; using heuristic fallback", clean_term, exc)
        if is_cs_subject:
            domain = "Computer Science"
            definition = f"Technical term: {clean_term}."
            context_explanation = f"In this passage, '{clean_term}' specifies an essential implementation detail or operational constraint."
            example = None
        else:
            domain = thematic_nature or deck_name or "General Studies"
            definition = f"Concept: {clean_term}."
            context_explanation = f"In this subject context, '{clean_term}' represents a core concept or term."
            example = None
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
