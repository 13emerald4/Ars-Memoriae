"""Technical lexicon, concordance, and concept definition service.

Uses local Qwen 2.5 Coder via Ollama to generate pedagogical, concise definitions
for unfamiliar terms encountered in cards, lessons, and code drills, with
instant SQLite cache lookup, deck concordance extraction, and authoritative
encyclopedic reference grounding.
"""

from __future__ import annotations

import logging
import re
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Card, Deck, LexiconCache, Note, User
from app.services.grading_service import GradingService, parse_json

log = logging.getLogger(__name__)

LEXICON_SYSTEM_PROMPT = """You are an expert educator, academic concordance specialist, and domain terminology tutor across diverse fields (humanities, languages, world history, sciences, arts, law, and computer science).
A student is reviewing a deck and asked for the definition of the term or phrase: "{term}".

CONTEXT WITHIN THE ACTIVE STUDY DECK:
- Deck Name: {deck_name}
- Subject / Thematic Nature: {thematic_nature}
{concordance_deck_occurrences}
{encyclopedic_reference}
{card_context}

CRITICAL DOMAIN & RELEVANCE RULES:
1. STRICT DECK-GROUNDED RELEVANCE:
   - Your definition MUST define "{term}" STRICTLY in the context of the active study deck ({deck_name} / {thematic_nature}) and the deck card occurrences shown above.
   - If "{term}" has multiple meanings, generic everyday acronyms, or meanings in unrelated fields (e.g. corporate slang, aviation, business, shipping, general tech), DO NOT provide those unrelated meanings!
   - You MUST define the specific academic, historical, cultural, linguistic, or technical meaning that applies to this deck's discipline.
   - For example: In a Spanish history, culture, or literature deck, "ETA" refers to "Euskadi Ta Askatasuna" (the armed Basque nationalist and separatist organization in Spain), NEVER "Expected Time of Arrival"!
   - If the subject is NOT computer science or programming:
     - DO NOT mention coding, software, programming, or computer science analogies.
     - Define the concept in its authentic discipline (e.g. Spanish History, Linguistics, World Literature, Art History, Biology, Law).
   - If "{term}" is genuinely about programming or computer science:
     - Provide a precise technical explanation and a concise code snippet or algorithmic example.

2. ACCURATE DEFINITION & EXPLANATION:
   - "definition": The primary 1-2 sentence core definition of the concept AS USED IN THIS SPECIFIC SUBJECT DOMAIN. Directly state what it means in this field. Be concise, direct, and pedagogically clear.
   - "context_explanation": 1-2 sentences explaining why this concept matters or how it is used within this deck's subject and cards.
   - "example": A concrete usage example, historical instance, or sentence appropriate to this domain.
   - "domain": The authentic discipline (e.g. 'Spanish History & Politics', 'Classical Sculpture', 'European Geography', 'Algorithms & Complexity').
   - "related_terms": 3-5 terms directly from this same subject domain.

Respond ONLY with a JSON object following this exact schema:
{{
  "definition": "1-2 sentence core definition in plain English explaining what it means in this subject domain.",
  "context_explanation": "1-2 sentences explaining its relevance and significance to this deck's cards.",
  "example": "A concrete domain-appropriate example (or null if not applicable).",
  "domain": "The authentic subject domain.",
  "related_terms": ["3-5 related terms within the same domain"]
}}
"""

CURATED_OFFLINE_DEFINITIONS: dict[str, dict] = {
    # Spanish History & Culture (SPAN 321 / Hispanic Studies)
    "eta": {
        "definition": "ETA (Euskadi Ta Askatasuna, 'Basque Homeland and Liberty') was an armed Basque nationalist and separatist organization in Spain.",
        "context_explanation": "From 1959 to 2011, ETA conducted a campaign of violent attacks, extortions, and assassinations seeking Basque independence, making its legacy a deeply significant and sensitive theme in Spanish history, politics, and culture.",
        "example": "Del País Vasco la película omite los muertos de ETA y la violencia de la kale borroka.",
        "domain": "Spanish History & Politics",
        "related_terms": ["Euskadi Ta Askatasuna", "kale borroka", "País Vasco", "nacionalismo vasco", "Transición española"],
    },
    "euskadi ta askatasuna": {
        "definition": "Euskadi Ta Askatasuna (ETA, 'Basque Homeland and Liberty') was an armed Basque nationalist and separatist organization in Spain.",
        "context_explanation": "Engaged in violent conflict seeking Basque self-determination from the Francoist dictatorship through the democratic era until its definitive dissolution in 2018.",
        "example": "La lucha armada de ETA cesó definitivamente en 2011 tras décadas de conflicto.",
        "domain": "Spanish History & Politics",
        "related_terms": ["ETA", "kale borroka", "País Vasco", "nacionalismo vasco"],
    },
    "kale borroka": {
        "definition": "Kale borroka (Basque for 'street struggle') refers to violent urban protest and low-intensity street violence carried out by radical Basque nationalist youth in Spain.",
        "context_explanation": "Used as an auxiliary tactic alongside ETA's armed struggle, involving vandalism, Molotov cocktails, and destruction of public infrastructure during the 1990s and 2000s.",
        "example": "La violencia de la kale borroka marcó el clima político del País Vasco.",
        "domain": "Spanish Politics & Society",
        "related_terms": ["ETA", "País Vasco", "abertzale", "nacionalismo vasco"],
    },
    "hieratismo": {
        "definition": "Hieratismo is an artistic and sculptural style characterized by solemn, rigid posture and stylized gestures, originating in ancient Eastern and Egyptian traditions.",
        "context_explanation": "In ancient Iberian art, sculptures like the Dama de Elche and Dama de Baza adopt Oriental hieratism combined with Greek naturalistic techniques.",
        "example": "La escultura íbera toma de Oriente el hieratismo, la solemnidad y la simetría del cabello.",
        "domain": "Art History & Ancient Spain",
        "related_terms": ["escultura íbera", "Dama de Elche", "arte votivo", "Tartesos"],
    },
    "celtíberos": {
        "definition": "The Celtiberians were pre-Roman Celtic-speaking peoples inhabiting the central-eastern Iberian Peninsula, formed by cultural convergence between native Iberians and migrating Celts.",
        "context_explanation": "Known for their fierce independence, guerrilla warfare, and heroic resistance against Roman conquest, famously culminating in the Siege of Numantia (133 BC).",
        "example": "Los celtíberos vivían en la Meseta en torno a ciudades como Numancia y resistieron a Roma.",
        "domain": "Ancient Iberian History",
        "related_terms": ["Numancia", "íberos", "celtas", "romanización", "Guerras Celtíberas"],
    },
    "celtiberos": {
        "definition": "The Celtiberians were pre-Roman Celtic-speaking peoples inhabiting the central-eastern Iberian Peninsula, formed by cultural convergence between native Iberians and migrating Celts.",
        "context_explanation": "Known for their fierce independence, guerrilla warfare, and heroic resistance against Roman conquest, famously culminating in the Siege of Numantia (133 BC).",
        "example": "Los celtíberos vivían en la Meseta en torno a ciudades como Numancia y resistieron a Roma.",
        "domain": "Ancient Iberian History",
        "related_terms": ["Numancia", "íberos", "celtas", "romanización", "Guerras Celtíberas"],
    },
    "hidalgo": {
        "definition": "An hidalgo (contraction of 'hijo de algo') was a member of the lower Spanish nobility, traditionally exempt from direct taxation.",
        "context_explanation": "Central to Spanish Golden Age literature and culture (as epitomized by Don Quijote), embodying chivalric ideals, personal honor, and pride despite frequent poverty.",
        "example": "Don Quijote de la Mancha es el hidalgo más célebre de la literatura española.",
        "domain": "Spanish History & Literature",
        "related_terms": ["hidalguía", "nobleza", "Siglo de Oro", "Don Quijote", "limpieza de sangre"],
    },
    "tartesos": {
        "definition": "Tartessos (Tarteso) was a wealthy semi-mythical ancient civilization situated in the Guadalquivir river basin of southwestern Spain, celebrated for metallurgy and trade with Phoenicians.",
        "context_explanation": "Described in Greek and biblical sources (Tarshish) as a kingdom of immense silver and gold wealth, functioning as a cultural bridge between indigenous Iberia and Eastern Mediterranean traders.",
        "example": "Hacia el 500 a.C. los cartagineses dominaron el sur peninsular y conquistaron Tartesos.",
        "domain": "Ancient Iberian History",
        "related_terms": ["fenicios", "Guadalquivir", "cartagineses", "Argantonio", "Iberia prerromana"],
    },
    "tartessos": {
        "definition": "Tartessos (Tarteso) was a wealthy semi-mythical ancient civilization situated in the Guadalquivir river basin of southwestern Spain, celebrated for metallurgy and trade with Phoenicians.",
        "context_explanation": "Described in Greek and biblical sources (Tarshish) as a kingdom of immense silver and gold wealth, functioning as a cultural bridge between indigenous Iberia and Eastern Mediterranean traders.",
        "example": "Hacia el 500 a.C. los cartagineses dominaron el sur peninsular y conquistaron Tartesos.",
        "domain": "Ancient Iberian History",
        "related_terms": ["fenicios", "Guadalquivir", "cartagineses", "Argantonio", "Iberia prerromana"],
    },
    "púnico": {
        "definition": "Punic refers to the Western Phoenicians and the civilization of ancient Carthage in North Africa and southern Iberia, as well as the language and culture they developed.",
        "context_explanation": "Derived from the Latin 'Poenicus', the term characterizes the Carthaginian presence in Iberia (e.g. Carthago Nova) and the three Punic Wars fought against Rome.",
        "example": "Púnico significa fenicio o cartaginés en el contexto de las colonias y guerras de la Península.",
        "domain": "Ancient Mediterranean History",
        "related_terms": ["Cartago", "Carthago Nova", "fenicios", "Guerras Púnicas", "Amílcar Barca"],
    },
    "punico": {
        "definition": "Punic refers to the Western Phoenicians and the civilization of ancient Carthage in North Africa and southern Iberia, as well as the language and culture they developed.",
        "context_explanation": "Derived from the Latin 'Poenicus', the term characterizes the Carthaginian presence in Iberia (e.g. Carthago Nova) and the three Punic Wars fought against Rome.",
        "example": "Púnico significa fenicio o cartaginés en el contexto de las colonias y guerras de la Península.",
        "domain": "Ancient Mediterranean History",
        "related_terms": ["Cartago", "Carthago Nova", "fenicios", "Guerras Púnicas", "Amílcar Barca"],
    },
    "reconquista": {
        "definition": "The Reconquista was a centuries-long period in medieval Iberian history (c. 718–1492) during which Christian kingdoms expanded southward to retake territories from Muslim rule.",
        "context_explanation": "Culminating in the fall of Granada in 1492 under the Catholic Monarchs, it profoundly shaped Spanish national identity, institutions, land distribution (latifundios), and religious unity.",
        "example": "La Reconquista concluyó en 1492 con la toma de Granada por los Reyes Católicos.",
        "domain": "Medieval Spanish History",
        "related_terms": ["Reyes Católicos", "Granada 1492", "Al-Ándalus", "latifundios", "repoblación"],
    },
    # Computer Science & Technical Systems
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


async def _fetch_encyclopedic_summary(term: str, is_spanish: bool = False) -> str | None:
    """Fetch authoritative encyclopedic extract from Wikipedia REST API to ground LLM generation."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            langs = ["es", "en"] if is_spanish else ["en", "es"]
            for lang in langs:
                encoded = term.replace(" ", "_")
                url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded}"
                resp = await client.get(url, headers={"User-Agent": "ArsMemoriae-Lexicon/1.0"})
                if resp.status_code == 200:
                    data = resp.json()
                    extract = data.get("extract")
                    title = data.get("title")
                    description = data.get("description")
                    if data.get("type") == "disambiguation":
                        continue
                    if extract and len(extract.strip()) > 20:
                        desc_str = f" ({description})" if description else ""
                        return f"Authoritative encyclopedic reference for '{title}'{desc_str}: {extract.strip()}"
    except Exception as exc:
        log.debug("Encyclopedic lookup skipped: %s", exc)
    return None


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
    target_deck_id = None
    card = None
    if card_id:
        try:
            import uuid
            card_uuid = uuid.UUID(card_id) if isinstance(card_id, str) else card_id
            card = await db.get(Card, card_uuid)
            if card:
                target_deck_id = card.deck_id
                deck = card.deck or (await db.get(Deck, card.deck_id))
                if not deck_name and deck:
                    deck_name = deck.name
                if not thematic_nature:
                    thematic_nature = card.thematic_nature or (deck.thematic_nature if deck else None)
                if card.note and card.note.field_values:
                    front_txt = card.note.field_values.get('Front') or card.note.field_values.get('front') or ''
                    back_txt = card.note.field_values.get('Back') or card.note.field_values.get('back') or ''
                    card_content = f"Front: {front_txt}\nBack: {back_txt}".strip()
        except Exception as exc:
            log.debug("Failed resolving card for lexicon lookup %s: %s", card_id, exc)

    # Detect discipline indicators
    combined_ctx_lower = f"{clean_term} {deck_name or ''} {thematic_nature or ''} {context or ''} {card_content}".lower()

    cs_indicators = [
        "programming", "computer science", "software", "coding", "code", "algorithm",
        "algorithms", "data structure", "data structures", "python", "typescript",
        "javascript", "java", "c++", "leetcode", "debugging", "compiler", "cpu",
        "hardware", "operating system", "concurrency", "database", "sql", "git",
        "cpsc", "cs1", "cs2", "cse", "binary", "floating-point"
    ]
    is_cs_subject = any(ind in combined_ctx_lower for ind in cs_indicators)

    spanish_indicators = [
        "span", "spanish", "españ", "espan", "cervantes", "vasco", "madrid", "andaluc",
        "celtas", "íberos", "iberos", "romano", "edad media", "reconquista", "franco",
        "siglo de oro", "literatura", "quijote", "lorca"
    ]
    is_spanish = any(ind in combined_ctx_lower for ind in spanish_indicators)

    # 1. Check database cache with domain validation
    cached_entry = (
        await db.execute(
            select(LexiconCache)
            .where(LexiconCache.term_normalized == norm_term)
            .order_by(LexiconCache.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if cached_entry:
        cached_domain_lower = (cached_entry.domain or "").lower()
        cached_def_lower = cached_entry.definition.lower()
        mismatched = False

        if is_cs_subject and not any(k in cached_domain_lower for k in ["computer", "programming", "algorithm", "software", "numerics"]):
            mismatched = True
        elif not is_cs_subject and any(k in cached_domain_lower for k in ["computer", "programming", "software", "algorithm"]):
            mismatched = True
        elif is_spanish and any(bad in cached_def_lower for bad in ["expected time of arrival", "estimated time of arrival"]):
            mismatched = True
        elif is_spanish and not any(k in cached_domain_lower or k in cached_def_lower for k in ["span", "españ", "vasc", "history", "culture", "literature", "latin", "art", "iber"]):
            mismatched = True

        if not mismatched:
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
        else:
            log.info("Bypassing incompatible cached lexicon entry for '%s' in context (%s)", clean_term, deck_name)

    # 2. Check curated offline dictionary for instant match
    if norm_term in CURATED_OFFLINE_DEFINITIONS:
        entry = CURATED_OFFLINE_DEFINITIONS[norm_term]
        entry_domain_lower = (entry.get("domain") or "").lower()
        entry_is_cs = any(k in entry_domain_lower for k in ["computer", "numerics", "complexity", "algorithms"])
        # Check domain compatibility:
        domain_matches = (
            (is_cs_subject and entry_is_cs) or
            (is_spanish and any(k in entry_domain_lower for k in ["spanish", "iberian", "spain"])) or
            (not is_cs_subject and not entry_is_cs)
        )
        if domain_matches:
            db_entry = LexiconCache(
                term_normalized=norm_term,
                term_display=clean_term,
                definition=entry["definition"],
                context_explanation=entry["context_explanation"],
                example=entry.get("example"),
                domain=entry.get("domain", "General Studies"),
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
                "domain": entry.get("domain", "General Studies"),
                "related_terms": entry.get("related_terms", []),
                "cached": False,
                "model_used": "curated_lexicon",
                "created_at": db_entry.created_at,
            }

    # 3. Concordance extraction from deck cards (True Concordance)
    deck_occurrences = []
    try:
        if not target_deck_id and deck_name:
            d_row = (await db.execute(select(Deck.id).where(Deck.name == deck_name).limit(1))).scalar_one_or_none()
            if d_row:
                target_deck_id = d_row

        if target_deck_id:
            subdeck_ids = (await db.execute(select(Deck.id).where(Deck.parent_id == target_deck_id))).scalars().all()
            deck_id_pool = [target_deck_id] + list(subdeck_ids)

            stmt = (
                select(Note.field_values)
                .join(Card, Card.note_id == Note.id)
                .where(Card.deck_id.in_(deck_id_pool))
                .limit(150)
            )
            deck_notes = (await db.execute(stmt)).scalars().all()
            pattern = re.compile(rf'\b{re.escape(clean_term)}\b', re.IGNORECASE)
            for fv in deck_notes:
                if not fv or not isinstance(fv, dict):
                    continue
                f_txt = fv.get('Front') or fv.get('front') or ''
                b_txt = fv.get('Back') or fv.get('back') or ''
                card_text = f"Q: {f_txt} | A: {b_txt}".strip()
                if pattern.search(card_text):
                    deck_occurrences.append(card_text)
                    if len(deck_occurrences) >= 3:
                        break
    except Exception as exc:
        log.debug("Error retrieving deck concordance occurrences: %s", exc)

    # 4. Fetch encyclopedic reference grounding
    encyclopedic_ref = await _fetch_encyclopedic_summary(clean_term, is_spanish=is_spanish)

    # 5. Build prompt
    occurrences_block = ""
    if deck_occurrences:
        occurrences_block = "\nACTUAL CARD OCCURRENCES IN THIS DECK:\n" + "\n---\n".join(f"- {o}" for o in deck_occurrences)

    encyclopedic_block = ""
    if encyclopedic_ref:
        encyclopedic_block = f"\nENCYCLOPEDIC REFERENCE GROUNDING:\n{encyclopedic_ref}\n"

    card_context_block = ""
    if card_content:
        card_context_block = f"\nACTIVE CARD CONTEXT:\n{card_content}"
    elif context and context.strip():
        card_context_block = f"\nREADING PASSAGE CONTEXT:\n{context.strip()[:1000]}"

    prompt = LEXICON_SYSTEM_PROMPT.format(
        term=clean_term,
        deck_name=deck_name or "Active Study Deck",
        thematic_nature=thematic_nature or "General academic subject",
        concordance_deck_occurrences=occurrences_block,
        encyclopedic_reference=encyclopedic_block,
        card_context=card_context_block,
    )

    # 6. Query local LLM (Qwen 2.5 Coder via Ollama)
    model_name = user.grading_model if user else settings.default_grading_model
    service = GradingService(model=model_name)

    try:
        raw_response = await service._generate(prompt, model=model_name)
        data = parse_json(raw_response)
        definition = data.get("definition") or f"A key concept: {clean_term}."
        context_explanation = data.get("context_explanation")
        example = data.get("example")
        domain = data.get("domain") or (thematic_nature or deck_name or ("Spanish History & Culture" if is_spanish else ("Computer Science" if is_cs_subject else "General Studies")))
        related_terms = data.get("related_terms") or []
        model_used = model_name

        # Safety post-processing: If Spanish context was tainted with Expected Time of Arrival
        if is_spanish and "expected time of arrival" in definition.lower():
            if encyclopedic_ref:
                definition = f"ETA (Euskadi Ta Askatasuna): armed Basque nationalist and separatist organization in Spain."
                domain = "Spanish History & Politics"
    except Exception as exc:
        log.warning("Ollama lexicon lookup failed for '%s': %s; using heuristic fallback", clean_term, exc)
        if encyclopedic_ref:
            definition = encyclopedic_ref.split(":", 1)[-1].strip() if ":" in encyclopedic_ref else encyclopedic_ref
            domain = "Spanish History & Culture" if is_spanish else "General Studies"
            context_explanation = f"In this deck, '{clean_term}' is an essential historical/subject term."
            example = None
        elif is_cs_subject:
            domain = "Computer Science"
            definition = f"Technical term: {clean_term}."
            context_explanation = f"In this passage, '{clean_term}' specifies an essential implementation detail or operational constraint."
            example = None
        else:
            domain = thematic_nature or deck_name or ("Spanish History & Culture" if is_spanish else "General Studies")
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
            .limit(limit * 2)
        )
    ).scalars().all()

    # Deduplicate by normalized term preserving most recent
    seen = set()
    out = []
    for r in rows:
        if r.term_normalized in seen:
            continue
        # Filter out corrupt/mismatched entries
        if "expected time of arrival" in r.definition.lower() and "world history" in (r.domain or "").lower():
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
        if len(out) >= limit:
            break
    return out
