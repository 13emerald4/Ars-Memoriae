"""Sister-card interference detection (§2 SuperMemo, §14 Phase 4).

Two cards interfere when they *look* alike but must be answered differently —
"hablar / to speak" against "hablarse / to talk to each other". That, not raw
similarity, is what makes a pair hard: identical-on-both-sides pairs are merely
duplicates, and are worth surfacing for a different reason.

So each candidate pair is scored on both halves independently and classified:

    front similar + back different  -> interference  (the confusable case)
    front similar + back similar    -> duplicate
    front different + back similar  -> convergent    (two prompts, one answer)

Similarity is computed locally — token Jaccard blended with character-trigram
cosine, which catches morphological variants that token overlap alone misses.
Nothing is sent anywhere: the spec's "no GPU/inference infra needed" applies
here too, and an embedding call per note-pair would be a real cost for a
feature that runs over the whole collection.

Comparing every pair is O(n²), so candidates are blocked through an inverted
index: only notes sharing a reasonably distinctive token are ever scored.
"""

from __future__ import annotations

import math
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Note, NoteType, SisterPair, User
from app.services.rendering import render

# A token indexing more than this share of the collection carries no signal and
# would blow up the candidate set ("the", "what", a deck-wide prefix).
MAX_BLOCK_SHARE = 0.10
MAX_BLOCK_ABSOLUTE = 400

# Calibrated against known-confusable pairs (Australia/Austria, hablar/hablarse,
# Krebs first/final step) versus unrelated ones. With the adaptive weighting
# below, real confusables bottom out around 0.53 and unrelated pairs top out
# around 0.30, so 0.52 sits in a wide gap rather than on a cliff edge.
FRONT_SIMILAR = 0.52
BACK_SIMILAR = 0.52
MIN_TEXT_CHARS = 3

_WORD_RE = re.compile(r"[\w']+", re.UNICODE)
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "do", "does", "for", "from",
    "how", "in", "is", "it", "of", "on", "or", "that", "the", "to", "was", "were", "what",
    "when", "where", "which", "who", "why", "with",
}


@dataclass
class Candidate:
    note_a: uuid.UUID
    note_b: uuid.UUID
    front_similarity: float
    back_similarity: float
    kind: str
    front_a: str
    front_b: str


# ── similarity primitives ───────────────────────────────────────────────────


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def tokens(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall(normalize(text)) if w not in _STOPWORDS}


def trigrams(text: str) -> set[str]:
    t = f"  {re.sub(r'[^a-z0-9 ]', '', normalize(text))} "
    return {t[i : i + 3] for i in range(len(t) - 2)} if len(t) >= 3 else set()


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def cosine(a: set[str], b: set[str]) -> float:
    """Cosine over binary set membership — a plain overlap ratio normalized by
    the geometric mean of the two sizes, so a short string matching inside a
    long one doesn't score as high as two genuinely similar strings."""
    if not a or not b:
        return 0.0
    return len(a & b) / math.sqrt(len(a) * len(b))


MAX_TOKEN_WEIGHT = 0.65
TOKEN_WEIGHT_SATURATES_AT = 3


def similarity(a: str, b: str) -> float:
    """Blend token overlap with character-trigram overlap.

    Tokens carry meaning; trigrams catch inflection and typos ("hablar" vs
    "hablarse"). The blend is *adaptive*, because a fixed weighting fails at
    both ends: on a one-word card Jaccard is brutally binary (0 or 1) and
    swamps the trigram signal that is the only thing distinguishing "hablar"
    from "hablarse", while on a long card trigrams rate any two sentences in
    the same language as vaguely alike. So token weight scales with how many
    tokens there actually are to compare, saturating at three.
    """
    if len(normalize(a)) < MIN_TEXT_CHARS or len(normalize(b)) < MIN_TEXT_CHARS:
        return 0.0
    tokens_a, tokens_b = tokens(a), tokens(b)
    if not tokens_a or not tokens_b:
        # Nothing but stopwords on one side. Trigrams would happily rate
        # "what is the of a" against "when is the of an" as near-identical,
        # but there is no content to base a confusability claim on.
        return 0.0
    n = min(len(tokens_a), len(tokens_b))
    w_token = MAX_TOKEN_WEIGHT * min(1.0, n / TOKEN_WEIGHT_SATURATES_AT)
    return w_token * jaccard(tokens_a, tokens_b) + (1 - w_token) * cosine(trigrams(a), trigrams(b))


def classify(front_sim: float, back_sim: float) -> str | None:
    front_close = front_sim >= FRONT_SIMILAR
    back_close = back_sim >= BACK_SIMILAR
    if front_close and back_close:
        return "duplicate"
    if front_close:
        return "interference"
    if back_close:
        return "convergent"
    return None


# ── detection ───────────────────────────────────────────────────────────────


def find_candidates(items: list[tuple[uuid.UUID, str, str]]) -> list[Candidate]:
    """``items`` is [(note_id, front, back)]. Returns classified pairs.

    Blocking keeps this near-linear on real collections: a pair is only scored
    if it shares a token that isn't collection-wide boilerplate.
    """
    by_id = {note_id: (front, back) for note_id, front, back in items}
    total = len(items)
    if total < 2:
        return []

    index: dict[str, list[uuid.UUID]] = defaultdict(list)
    for note_id, front, back in items:
        for token in tokens(front) | tokens(back):
            index[token].append(note_id)

    cap = max(2, min(MAX_BLOCK_ABSOLUTE, int(total * MAX_BLOCK_SHARE)))
    pairs: set[tuple[uuid.UUID, uuid.UUID]] = set()
    for note_ids in index.values():
        if len(note_ids) < 2 or len(note_ids) > cap:
            continue
        for i, a in enumerate(note_ids):
            for b in note_ids[i + 1 :]:
                pairs.add((a, b) if str(a) < str(b) else (b, a))

    out: list[Candidate] = []
    for a, b in pairs:
        front_a, back_a = by_id[a]
        front_b, back_b = by_id[b]
        front_sim = similarity(front_a, front_b)
        back_sim = similarity(back_a, back_b)
        kind = classify(front_sim, back_sim)
        if kind is None:
            continue
        out.append(
            Candidate(
                note_a=a,
                note_b=b,
                front_similarity=round(front_sim, 4),
                back_similarity=round(back_sim, 4),
                kind=kind,
                front_a=front_a,
                front_b=front_b,
            )
        )

    # Most-confusable first: interference before duplicates, then by how alike.
    order = {"interference": 0, "convergent": 1, "duplicate": 2}
    out.sort(key=lambda c: (order[c.kind], -max(c.front_similarity, c.back_similarity)))
    return out


async def scan_user(db: AsyncSession, user: User, limit: int = 200) -> dict:
    """Recompute sister pairs for one user, preserving dismissals."""
    rows = (
        await db.execute(
            select(Note, NoteType)
            .join(NoteType, NoteType.id == Note.note_type_id)
            .where(Note.user_id == user.id)
        )
    ).all()

    items: list[tuple[uuid.UUID, str, str]] = []
    for note, note_type in rows:
        # A note's first card is representative enough for interference; scoring
        # every cloze deletion separately mostly finds a note against itself.
        front, back = render(note_type.template_kind, note.field_values or {}, "default")
        if note_type.template_kind == "cloze":
            front, back = render(note_type.template_kind, note.field_values or {}, "c1")
        if not front.strip() and not back.strip():
            continue
        items.append((note.id, front, back))

    candidates = find_candidates(items)[:limit]

    existing = {
        (p.note_a_id, p.note_b_id): p
        for p in (await db.scalars(select(SisterPair).where(SisterPair.user_id == user.id))).all()
    }
    seen: set[tuple[uuid.UUID, uuid.UUID]] = set()
    created = 0

    for cand in candidates:
        key = (cand.note_a, cand.note_b)
        seen.add(key)
        pair = existing.get(key)
        if pair is None:
            db.add(
                SisterPair(
                    user_id=user.id,
                    note_a_id=cand.note_a,
                    note_b_id=cand.note_b,
                    front_similarity=cand.front_similarity,
                    back_similarity=cand.back_similarity,
                    kind=cand.kind,
                )
            )
            created += 1
        elif pair.status != "dismissed":
            # Refresh scores on edited notes, but never resurrect a dismissal:
            # the user has already said these two don't confuse them.
            pair.front_similarity = cand.front_similarity
            pair.back_similarity = cand.back_similarity
            pair.kind = cand.kind

    for key, pair in existing.items():
        if key not in seen and pair.status == "open":
            await db.delete(pair)

    await db.commit()
    counts: dict[str, int] = defaultdict(int)
    for c in candidates:
        counts[c.kind] += 1
    return {
        "notes_scanned": len(items),
        "pairs_found": len(candidates),
        "pairs_created": created,
        "by_kind": dict(counts),
    }


async def spacing_conflicts(db: AsyncSession, user: User) -> dict[uuid.UUID, set[uuid.UUID]]:
    """note_id -> notes it should be kept away from in a session.

    Mnemosyne's "keep related/confusable cards apart" (§2), applied to the
    composed queue rather than to scheduling: showing two confusable cards
    back to back is exactly how the interference gets reinforced.
    """
    pairs = (
        await db.scalars(
            select(SisterPair).where(
                SisterPair.user_id == user.id,
                SisterPair.status == "open",
                SisterPair.kind.in_(("interference", "duplicate")),
            )
        )
    ).all()
    graph: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    for p in pairs:
        graph[p.note_a_id].add(p.note_b_id)
        graph[p.note_b_id].add(p.note_a_id)
    return graph
