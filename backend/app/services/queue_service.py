"""Priority queue & session composition (§9) + review-load guardrails (§3.1).

This is the piece Anki does not have: session content is chosen by priority and
a time budget, not by strict due-date order, and due reviews / new cards / IR
extracts are interleaved rather than block-scheduled.

Composition, in order:
  1. Eligible pool  — due reviews, new cards under today's intake cap, active
     IR extracts. Suspended and leech-flagged cards are excluded.
  2. Ranking        — priority descending, with an overdue boost derived from
     FSRS retrievability so a low-priority card cannot starve forever.
  3. Budget fill    — the day's time budget is split across the three streams
     by the user's weights, then filled from the top of each ranked stream.
  4. Interleaving   — streams are woven together by normalized position.

Registered on the ``queue_composer`` seam (§12).
"""

from __future__ import annotations

import math
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import and_, false, func, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Card,
    CardReference,
    Deck,
    Extract,
    Note,
    QueueConfig,
    ReviewLog,
    Source,
    User,
)
from app.services import registry
from app.services.fsrs_service import FSRSService
from app.services.rendering import occlusion_payload, render
from app.services.tree_service import (
    BranchScope,
    branch_scope,
    has_any_gating,
    locked_entity_ids,
)

OVERDUE_BOOST_MAX = 25.0  # priority points a fully-forgotten card can gain
MIN_SECONDS_PER_ITEM = 3.0

# How many due cards to load as ranking candidates, relative to the session
# size. Everything above this is provably irrelevant for realistic priority
# spreads and, past the floor, far beyond what any session shows.
CANDIDATE_POOL_MULTIPLIER = 4
MIN_CANDIDATE_POOL = 500
MAX_CANDIDATE_POOL = 5000
# Recent latencies are enough to estimate a median; a full 30-day scan is not.
LATENCY_SAMPLE_SIZE = 500


def candidate_pool_size(review_cap: int) -> int:
    if review_cap <= 0:
        return 0
    return max(MIN_CANDIDATE_POOL, min(MAX_CANDIDATE_POOL, review_cap * CANDIDATE_POOL_MULTIPLIER))


@dataclass
class ComposedItem:
    kind: Literal["card", "extract"]
    id: str
    deck_or_source_id: str
    priority: int
    effective_priority: float
    front: str | None = None
    back: str | None = None
    extract_content: str | None = None
    source_title: str | None = None
    deck_name: str | None = None
    state: str | None = None
    template_kind: str | None = None
    grading_profile: str | None = None
    estimated_seconds: float = 12.0
    note_id: str | None = None
    occlusion: dict | None = None
    references: list[dict] = field(default_factory=list)
    starter_code: str | None = None
    starter_tests: str | None = None
    test_cases: list[dict] = field(default_factory=list)
    time_complexity: str | None = None
    space_complexity: str | None = None
    edge_cases: list[str] = field(default_factory=list)
    title: str | None = None
    difficulty: str | None = None
    category: str | None = None
    active_weaknesses: list[str] = field(default_factory=list)
    weakness_history: list[dict] = field(default_factory=list)
    deck_documentation: str | None = None
    deck_thematic_nature: str | None = None
    deck_source_documents: list = field(default_factory=list)
    card_documentation: str | None = None
    card_thematic_nature: str | None = None
    card_source_documents: list = field(default_factory=list)


@dataclass
class SessionPlan:
    items: list[ComposedItem] = field(default_factory=list)
    budget_seconds: float = 0.0
    counts: dict[str, int] = field(default_factory=dict)
    caps: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def start_of_day(now: datetime) -> datetime:
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


async def get_queue_config(db: AsyncSession, user: User) -> QueueConfig:
    cfg = await db.get(QueueConfig, user.id)
    if cfg is None:
        cfg = QueueConfig(user_id=user.id)
        db.add(cfg)
        await db.commit()
        await db.refresh(cfg)
    return cfg


async def _counts_today(db: AsyncSession, user: User, now: datetime) -> tuple[int, int]:
    """(reviews done today, new cards introduced today) — drives the caps."""
    since = start_of_day(now)
    rows = await db.execute(
        select(ReviewLog.state_before, func.count())
        .join(Card, Card.id == ReviewLog.card_id)
        .join(Deck, Deck.id == Card.deck_id)
        .where(Deck.user_id == user.id, ReviewLog.reviewed_at >= since)
        .group_by(ReviewLog.state_before)
    )
    reviews = news = 0
    for state_before, count in rows.all():
        if state_before == "new":
            news += count
        else:
            reviews += count
    return reviews, news


async def measured_seconds_per_review(db: AsyncSession, user: User, fallback: float) -> float:
    """§9.3 — refine the per-item time estimate from actual logged timing once
    there is enough of it, instead of trusting the configured constant forever."""
    since = datetime.now(UTC) - timedelta(days=30)
    rows = await db.execute(
        select(ReviewLog.latency_ms)
        .join(Card, Card.id == ReviewLog.card_id)
        .join(Deck, Deck.id == Card.deck_id)
        .where(
            Deck.user_id == user.id,
            ReviewLog.reviewed_at >= since,
            ReviewLog.latency_ms.isnot(None),
        )
        .order_by(ReviewLog.reviewed_at.desc())
        .limit(LATENCY_SAMPLE_SIZE)
    )
    latencies = sorted(r[0] for r in rows.all() if r[0] and r[0] > 0)
    if len(latencies) < 30:
        return fallback
    median_ms = latencies[len(latencies) // 2]
    # + 3s of grading-review/keystroke overhead the latency timer doesn't cover.
    return max(MIN_SECONDS_PER_ITEM, median_ms / 1000.0 + 3.0)


def review_allowance(
    todays_due: int, overdue_backlog: int, spread_days: int, hard_cap: int, done_today: int
) -> int:
    """Daily review cap with overflow smoothing (§3.1).

    A backlog from missed days is spread over ``spread_days`` instead of being
    dumped at once — the specific failure mode ("miss a few days and 100 due
    becomes 800") that §13 identifies as the real driver of algorithm-shopping.
    """
    smoothed = todays_due + math.ceil(overdue_backlog / max(1, spread_days))
    return max(0, min(smoothed, hard_cap) - done_today)


def _effective_priority_sql():
    """Priority as SQL, so ranking happens in the database: NULL on a card
    means "inherit the deck default" (§5)."""
    return func.coalesce(Card.priority, Deck.default_priority)


def _eligible_filter(
    user: User,
    scope: BranchScope | None = None,
    locked_deck_ids: set | None = None,
):
    """Ownership + suspension, plus the branch restriction when one is set,
    plus mastery gating when the user has any configured.

    A card is inside a branch either because its deck is, or because it was
    carved out of an extract that is (``origin_extract_id``) — so studying an
    article's branch covers the cards it produced, not just the reading left.
    """
    conditions = [
        Deck.user_id == user.id,
        Card.suspended.is_(False),
        Card.leech_flag.is_(False),
    ]
    if scope is not None:
        reachable = []
        if scope.deck_ids:
            reachable.append(Card.deck_id.in_(scope.deck_ids))
        if scope.extract_ids:
            reachable.append(Card.origin_extract_id.in_(scope.extract_ids))
        # An empty branch matches nothing, rather than silently matching all.
        conditions.append(or_(*reachable) if reachable else false())
    if locked_deck_ids:
        conditions.append(Card.deck_id.notin_(locked_deck_ids))
    return tuple(conditions)


def _extract_scope_filter(scope: BranchScope | None, locked_source_ids: set | None = None):
    conditions = []
    if scope is not None:
        conditions.append(Extract.id.in_(scope.extract_ids) if scope.extract_ids else false())
    if locked_source_ids:
        conditions.append(Source.id.notin_(locked_source_ids))
    return and_(*conditions) if conditions else true()


async def eligible_counts(
    db: AsyncSession,
    user: User,
    now: datetime,
    scope: BranchScope | None = None,
    locked_deck_ids: set | None = None,
) -> dict[str, int]:
    """Exact pool sizes via COUNT, independent of how many rows we then fetch.

    The session header and the §3.1 backlog-smoothing arithmetic both need real
    totals, but neither needs the rows — and materialising 30k ORM objects to
    call len() on them is what made this endpoint take seconds on an imported
    collection.
    """
    today = start_of_day(now)

    async def count(*extra) -> int:
        return int(
            await db.scalar(
                select(func.count())
                .select_from(Card)
                .join(Deck, Deck.id == Card.deck_id)
                .where(*_eligible_filter(user, scope, locked_deck_ids), *extra)
            )
            or 0
        )

    due_total = await count(Card.state != "new", Card.due.isnot(None), Card.due <= now)
    overdue = await count(Card.state != "new", Card.due.isnot(None), Card.due < today)
    new_total = await count(Card.state == "new")
    return {"due_total": due_total, "overdue_total": overdue, "new_total": new_total}


async def fetch_due_candidates(
    db: AsyncSession,
    user: User,
    now: datetime,
    limit: int,
    scope: BranchScope | None = None,
    locked_deck_ids: set | None = None,
) -> list[Card]:
    """Bounded candidate pool for due reviews, ranked in SQL.

    Final ranking adds an overdue boost that FSRS retrievability can only give
    us in Python (§9.2), so we can't order fully in the database. We don't need
    to: the boost is capped at OVERDUE_BOOST_MAX, so ordering by base priority
    and then by how overdue a card is puts every plausible winner near the top.
    We take a pool several times the size of the session and rank that exactly.
    Beyond the pool ceiling the choice is approximate — but the ceiling is far
    larger than any session, so it never shows up in what a user sees.
    """
    if limit <= 0:
        return []
    rows = await db.execute(
        select(Card)
        .join(Deck, Deck.id == Card.deck_id)
        .where(
            *_eligible_filter(user, scope, locked_deck_ids),
            Card.state != "new",
            Card.due.isnot(None),
            Card.due <= now,
        )
        .order_by(_effective_priority_sql().desc(), Card.due.asc())
        .limit(limit)
    )
    return list(rows.scalars())


async def fetch_new_candidates(
    db: AsyncSession,
    user: User,
    limit: int,
    scope: BranchScope | None = None,
    locked_deck_ids: set | None = None,
) -> list[Card]:
    """New cards rank purely on priority — no boost — so SQL is exact here."""
    if limit <= 0:
        return []
    rows = await db.execute(
        select(Card)
        .join(Deck, Deck.id == Card.deck_id)
        .where(*_eligible_filter(user, scope, locked_deck_ids), Card.state == "new")
        .order_by(_effective_priority_sql().desc(), Card.id)
        .limit(limit)
    )
    return list(rows.scalars())


async def _eligible_extracts(
    db: AsyncSession,
    user: User,
    now: datetime,
    limit: int = 200,
    scope: BranchScope | None = None,
    locked_source_ids: set | None = None,
) -> list[tuple[Extract, Source]]:
    rows = await db.execute(
        select(Extract, Source)
        .join(Source, Source.id == Extract.source_id)
        .where(
            Source.user_id == user.id,
            Source.status == "active",
            Source.for_reading.is_(True),
            Extract.status == "active",
            or_(Extract.next_shown_at.is_(None), Extract.next_shown_at <= now),
            _extract_scope_filter(scope, locked_source_ids),
        )
        .order_by(func.coalesce(Extract.priority, Source.priority).desc())
        .limit(limit)
    )
    return list(rows.all())


async def count_eligible_extracts(
    db: AsyncSession,
    user: User,
    now: datetime,
    scope: BranchScope | None = None,
    locked_source_ids: set | None = None,
) -> int:
    return int(
        await db.scalar(
            select(func.count())
            .select_from(Extract)
            .join(Source, Source.id == Extract.source_id)
            .where(
                Source.user_id == user.id,
                Source.status == "active",
                Source.for_reading.is_(True),
                Extract.status == "active",
                or_(Extract.next_shown_at.is_(None), Extract.next_shown_at <= now),
                _extract_scope_filter(scope, locked_source_ids),
            )
        )
        or 0
    )


def _overdue_boost(card: Card, fsrs: FSRSService, now: datetime) -> float:
    """More overdue -> higher effective priority (§9.2).

    Uses FSRS retrievability rather than raw days-overdue, so "overdue" is
    measured against what the card's own stability predicted.
    """
    if card.state == "new" or card.stability is None or card.last_review is None:
        return 0.0
    try:
        fc = FSRSService.to_fsrs_card(
            state=card.state,
            stability=card.stability,
            difficulty=card.difficulty,
            step=card.step,
            due=card.due,
            last_review=card.last_review,
        )
        r = fsrs.retrievability(fc, now)
    except Exception:
        return 0.0
    return max(0.0, min(1.0, 1.0 - r)) * OVERDUE_BOOST_MAX


def _card_item(card: Card, effective: float, seconds: float) -> ComposedItem:
    note = card.note
    kind = note.note_type.template_kind
    front, back = render(kind, note.field_values or {}, card.template_slot)
    fv = note.field_values or {}
    return ComposedItem(
        kind="card",
        id=str(card.id),
        deck_or_source_id=str(card.deck_id),
        priority=card.effective_priority,
        effective_priority=effective,
        front=front,
        back=back,
        deck_name=card.deck.name,
        state=card.state,
        template_kind=kind,
        grading_profile=note.note_type.grading_profile,
        estimated_seconds=seconds,
        note_id=str(card.note_id),
        occlusion=occlusion_payload(fv, card.template_slot)
        if kind == "image_occlusion"
        else None,
        starter_code=fv.get("starter_code"),
        starter_tests=fv.get("starter_tests"),
        test_cases=fv.get("test_cases") or [],
        time_complexity=fv.get("time_complexity"),
        space_complexity=fv.get("space_complexity"),
        edge_cases=fv.get("edge_cases") or [],
        title=fv.get("title"),
        difficulty=fv.get("difficulty"),
        category=fv.get("category"),
        active_weaknesses=card.active_weaknesses or [],
        weakness_history=card.weakness_history or [],
        deck_documentation=card.deck.documentation if card.deck else None,
        deck_thematic_nature=card.deck.thematic_nature if card.deck else None,
        deck_source_documents=list(card.deck.source_documents or []) if card.deck else [],
        card_documentation=card.documentation or (card.deck.documentation if card.deck else None),
        card_thematic_nature=card.thematic_nature or (card.deck.thematic_nature if card.deck else None),
        card_source_documents=list(card.source_documents or (card.deck.source_documents if card.deck else [])),
    )


async def attach_references(db: AsyncSession, items: list[ComposedItem]) -> None:
    """Load each card's document citations in one query, after the cut.

    Runs on the *final* item list rather than inside ``_card_item`` so the cost
    is bounded by what the session actually shows — one extra query for a
    25-item preview, and for ``/queue/next`` a single row. Building it into
    per-card rendering would put a query behind every candidate the ranker
    merely considered.
    """
    card_ids = [_as_uuid(i.id) for i in items if i.kind == "card"]
    if not card_ids:
        return

    rows = (
        await db.execute(
            select(CardReference, Extract.content)
            .outerjoin(Extract, Extract.id == CardReference.extract_id)
            .where(CardReference.card_id.in_(card_ids))
            .order_by(CardReference.position, CardReference.created_at)
        )
    ).all()
    if not rows:
        return

    by_card: dict[str, list[dict]] = {}
    for ref, passage in rows:
        by_card.setdefault(str(ref.card_id), []).append(
            {
                "quote": ref.quote or "",
                "quote_verified": ref.quote_verified,
                "locator": ref.locator,
                "source_title": ref.source_title,
                "extract_id": str(ref.extract_id) if ref.extract_id else None,
                "passage": passage,
            }
        )
    for item in items:
        if item.kind == "card":
            item.references = by_card.get(item.id, [])


def space_sisters(
    items: list[ComposedItem], conflicts: dict, min_gap: int = 3
) -> list[ComposedItem]:
    """Push confusable cards apart inside the session (§2, Mnemosyne).

    Showing two cards you already mix up back to back is precisely how the
    interference gets reinforced. This is a *reordering*, never a drop: an item
    that can't be separated is placed anyway once the search window is
    exhausted, so nothing silently vanishes from a session.
    """
    if not conflicts:
        return items

    remaining = list(items)
    out: list[ComposedItem] = []
    while remaining:
        chosen = 0
        for idx, candidate in enumerate(remaining):
            note_id = candidate.note_id
            if note_id is None:
                chosen = idx
                break
            clashes = conflicts.get(_as_uuid(note_id), set())
            if not clashes:
                chosen = idx
                break
            recent = {out[-i].note_id for i in range(1, min(min_gap, len(out)) + 1)}
            if not any(str(c) in recent for c in clashes):
                chosen = idx
                break
        else:
            chosen = 0  # everything clashes; keep priority order rather than stall
        out.append(remaining.pop(chosen))
    return out


def _as_uuid(value):
    import uuid as _uuid_mod

    try:
        return _uuid_mod.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return value


def _interleave(streams: list[list[ComposedItem]]) -> list[ComposedItem]:
    """Weave the streams together by normalized position (§9.4).

    Stream *sizes* were already set by the weighted budget split, so evenly
    interleaving by relative position reproduces the configured mix without a
    second weighting pass.
    """
    keyed: list[tuple[float, int, ComposedItem]] = []
    for s_idx, stream in enumerate(streams):
        n = len(stream)
        for i, item in enumerate(stream):
            keyed.append(((i + 0.5) / n, s_idx, item))
    keyed.sort(key=lambda t: (t[0], t[1]))
    return [item for _, _, item in keyed]


async def deck_scope(db: AsyncSession, user: User, root_deck_id: uuid.UUID) -> BranchScope | None:
    deck = await db.get(Deck, root_deck_id)
    if deck is None or deck.user_id != user.id:
        return None
    all_decks = (await db.scalars(select(Deck).where(Deck.user_id == user.id))).all()
    children: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for d in all_decks:
        if d.parent_id:
            children[d.parent_id].append(d.id)
    deck_ids = {root_deck_id}
    queue = [root_deck_id]
    while queue:
        curr = queue.pop(0)
        for child_id in children.get(curr, []):
            if child_id not in deck_ids:
                deck_ids.add(child_id)
                queue.append(child_id)
    return BranchScope(node_id=root_deck_id, title=deck.name, deck_ids=deck_ids)


async def compose_session(
    db: AsyncSession,
    user: User,
    *,
    now: datetime | None = None,
    limit: int | None = None,
    branch=None,
    deck=None,
) -> SessionPlan:
    now = now or datetime.now(UTC)
    cfg = await get_queue_config(db, user)
    fsrs = FSRSService(
        weights=user.fsrs_parameters, desired_retention=user.desired_retention, fuzz=False
    )

    # Scoping: A branch restricts to a knowledge tree subtree; a deck restricts
    # to that deck and all its recursive subdecks. If neither is specified,
    # scope is None and the session covers the entire collection all at once.
    scope = None
    if branch:
        scope = await branch_scope(db, user, branch)
    elif deck:
        scope = await deck_scope(db, user, deck)

    # Mastery gating (§ Tree): excluded up front so every downstream query —
    # counts, candidates, extracts — simply never sees a locked card. The
    # existence check keeps this at one indexed query for the overwhelmingly
    # common case of no prerequisites configured.
    locked_deck_ids: set = set()
    locked_source_ids: set = set()
    if await has_any_gating(db, user):
        locked_deck_ids, locked_source_ids = await locked_entity_ids(db, user)

    # Counts come from COUNT(*); only a bounded pool of rows is ever loaded.
    counts = await eligible_counts(db, user, now, scope, locked_deck_ids)
    reviews_done, new_done = await _counts_today(db, user, now)

    # ── §3.1 caps ───────────────────────────────────────────────────────────
    overdue_total = counts["overdue_total"]
    todays = counts["due_total"] - overdue_total
    review_cap = review_allowance(
        todays, overdue_total, user.backlog_spread_days, user.daily_review_limit, reviews_done
    )
    new_cap = max(0, user.daily_new_limit - new_done)

    due_cards = await fetch_due_candidates(
        db, user, now, candidate_pool_size(review_cap), scope, locked_deck_ids
    )
    new_cards = await fetch_new_candidates(db, user, new_cap, scope, locked_deck_ids)
    extract_rows = await _eligible_extracts(
        db, user, now, scope=scope, locked_source_ids=locked_source_ids
    )
    ir_total = await count_eligible_extracts(db, user, now, scope, locked_source_ids)

    # ── §9.2 ranking ────────────────────────────────────────────────────────
    ranked_due = sorted(
        ((c, c.effective_priority + _overdue_boost(c, fsrs, now)) for c in due_cards),
        key=lambda t: -t[1],
    )[:review_cap]
    ranked_new = [(c, float(c.effective_priority)) for c in new_cards]  # already ordered in SQL
    ranked_ir = sorted(
        (
            (e, s, float(e.priority if e.priority is not None else s.priority))
            for e, s in extract_rows
        ),
        key=lambda t: -t[2],
    )

    # ── §9.3 time-budget fill ───────────────────────────────────────────────
    budget = user.queue_time_budget_minutes * 60.0
    weights = {
        "review": max(0.0, cfg.review_weight),
        "new": max(0.0, cfg.new_weight),
        "ir": max(0.0, cfg.ir_weight),
    }
    total_w = sum(weights.values()) or 1.0
    sec_review = await measured_seconds_per_review(db, user, cfg.seconds_per_review)
    sec_ir = max(MIN_SECONDS_PER_ITEM, cfg.seconds_per_ir_extract)

    def take(n_available: int, weight: float, per_item: float) -> int:
        share = budget * (weight / total_w)
        return min(n_available, int(share // per_item))

    n_review = take(len(ranked_due), weights["review"], sec_review)
    n_new = take(len(ranked_new), weights["new"], sec_review)
    n_ir = take(len(ranked_ir), weights["ir"], sec_ir)

    # Reallocate slack from streams that ran dry, so an empty IR list does not
    # silently shrink the session.
    leftover = budget - (n_review + n_new) * sec_review - n_ir * sec_ir
    for _ in range(3):
        if leftover < sec_review:
            break
        grew = False
        if n_review < len(ranked_due):
            extra = min(len(ranked_due) - n_review, int(leftover // sec_review))
            n_review += extra
            leftover -= extra * sec_review
            grew = extra > 0
        if leftover >= sec_review and n_new < len(ranked_new):
            extra = min(len(ranked_new) - n_new, int(leftover // sec_review))
            n_new += extra
            leftover -= extra * sec_review
            grew = grew or extra > 0
        if leftover >= sec_ir and n_ir < len(ranked_ir):
            extra = min(len(ranked_ir) - n_ir, int(leftover // sec_ir))
            n_ir += extra
            leftover -= extra * sec_ir
            grew = grew or extra > 0
        if not grew:
            break

    review_stream = [_card_item(c, p, sec_review) for c, p in ranked_due[:n_review]]
    new_stream = [_card_item(c, p, sec_review) for c, p in ranked_new[:n_new]]
    ir_stream = [
        ComposedItem(
            kind="extract",
            id=str(e.id),
            deck_or_source_id=str(s.id),
            priority=int(p),
            effective_priority=p,
            extract_content=e.content,
            source_title=s.title,
            estimated_seconds=sec_ir,
        )
        for e, s, p in ranked_ir[:n_ir]
    ]

    items = _interleave([s for s in (review_stream, new_stream, ir_stream) if s])

    # §2 (Mnemosyne): keep confusable cards apart. Done after interleaving so
    # it only reorders within the session the budget already decided on.
    from app.services.interference_service import spacing_conflicts

    conflicts = await spacing_conflicts(db, user)
    items = space_sisters(items, conflicts)

    if limit:
        items = items[:limit]
    await attach_references(db, items)

    notes: list[str] = []
    if overdue_total and review_cap < counts["due_total"]:
        notes.append(
            f"{overdue_total} overdue cards are being spread over "
            f"{user.backlog_spread_days} days instead of shown all at once."
        )
    if not user.llm_grading_consent:
        notes.append("LLM grading is off — answers are graded manually.")
    if scope is not None:
        notes.append(
            f"Scoped to the “{scope.title}” branch — "
            f"{len(scope.deck_ids)} deck(s) and {len(scope.extract_ids)} extract(s)."
            if not scope.empty
            else f"The “{scope.title}” branch has nothing in it yet."
        )
    if locked_deck_ids or locked_source_ids:
        notes.append(
            "Some material is locked behind a mastery gate — check the Tree to see what's next."
        )

    return SessionPlan(
        items=items,
        budget_seconds=budget,
        counts={
            "review": len(review_stream),
            "new": len(new_stream),
            "ir": len(ir_stream),
            "due_total": counts["due_total"],
            "overdue_total": overdue_total,
            "new_total": counts["new_total"],
            "ir_total": ir_total,
        },
        caps={
            "review_remaining": review_cap,
            "new_remaining": new_cap,
            "reviews_done_today": reviews_done,
            "new_done_today": new_done,
        },
        notes=notes,
    )


async def next_item(db: AsyncSession, user: User, *, branch=None, deck=None) -> ComposedItem | None:
    plan = await compose_session(db, user, limit=1, branch=branch, deck=deck)
    return plan.items[0] if plan.items else None


registry.register("queue_composer", "priority_time_budget", compose_session, default=True)


async def compose_due_date_only(
    db: AsyncSession,
    user: User,
    *,
    now: datetime | None = None,
    limit: int | None = None,
    branch=None,
) -> SessionPlan:
    """The Phase-1 composer (§14.1 step 5): strict due-date order, no priority
    weighting. Kept registered as an alternative strategy — it is the fallback
    if a user turns priority composition off, and it is what the queue tests
    compare against."""
    now = now or datetime.now(UTC)
    scope = await branch_scope(db, user, branch) if branch else None
    locked_deck_ids: set = set()
    if await has_any_gating(db, user):
        locked_deck_ids, _ = await locked_entity_ids(db, user)
    reviews_done, new_done = await _counts_today(db, user, now)
    review_cap = max(0, user.daily_review_limit - reviews_done)
    new_cap = max(0, user.daily_new_limit - new_done)

    # Strict due-date order, bounded in SQL like the priority composer.
    due_rows = await db.execute(
        select(Card)
        .join(Deck, Deck.id == Card.deck_id)
        .where(
            *_eligible_filter(user, scope, locked_deck_ids),
            Card.state != "new",
            Card.due.isnot(None),
            Card.due <= now,
        )
        .order_by(Card.due.asc())
        .limit(review_cap)
    )
    due_cards = list(due_rows.scalars())
    new_cards = await fetch_new_candidates(db, user, new_cap, scope, locked_deck_ids)

    items = [_card_item(c, float(c.effective_priority), 12.0) for c in due_cards]
    items += [_card_item(c, float(c.effective_priority), 12.0) for c in new_cards]
    if limit:
        items = items[:limit]
    await attach_references(db, items)
    return SessionPlan(
        items=items,
        counts={"review": len(due_cards), "new": len(new_cards)},
        caps={"review_remaining": review_cap, "new_remaining": new_cap},
    )


registry.register("queue_composer", "due_date_only", compose_due_date_only)


async def compose_deck_persist_queue(
    db: AsyncSession,
    user: User,
    deck_id: uuid.UUID,
) -> list[ComposedItem]:
    """Load all active (non-suspended) cards in a deck formatted as ComposedItems for persist mode."""
    deck = await db.get(Deck, deck_id)
    if deck is None or deck.user_id != user.id:
        return []

    stmt = (
        select(Card)
        .join(Deck, Deck.id == Card.deck_id)
        .where(
            Card.deck_id == deck.id,
            Card.suspended.is_(False),
        )
        .order_by(
            Card.due.is_(None),
            Card.due.asc(),
            _effective_priority_sql().desc(),
            Card.id.asc(),
        )
    )
    rows = await db.execute(stmt)
    cards = list(rows.scalars())
    items = [_card_item(c, float(c.effective_priority), 12.0) for c in cards]
    await attach_references(db, items)
    return items


async def compose_deck_all_cards_run_queue(
    db: AsyncSession,
    user: User,
    deck_id: uuid.UUID,
) -> list[ComposedItem]:
    """Load all active cards in a deck sorted consecutively from easiest to hardest.

    Difficulty scoring:
    1. Categorical difficulty in note field values:
       - 'Easy' -> baseline 2.0
       - 'Medium' -> baseline 5.0
       - 'Hard' -> baseline 8.0
       - Unrated -> baseline 4.5
    2. FSRS difficulty (card.difficulty, 1.0 - 10.0):
       - If present, incorporates into baseline
    3. Review log history adjustment:
       - Latest rating: Easy (-1.5), Good (-0.5), Hard (+1.5), Again (+2.5)
       - Card lapse count: +0.4 per lapse
       - Leech flag: +2.5

    Cards are sorted ascending by difficulty score (easiest seen first, hardest seen last).
    """
    deck = await db.get(Deck, deck_id)
    if deck is None or deck.user_id != user.id:
        return []

    stmt = (
        select(Card, Note)
        .join(Deck, Deck.id == Card.deck_id)
        .join(Note, Note.id == Card.note_id)
        .where(
            Card.deck_id == deck.id,
            Card.suspended.is_(False),
        )
    )
    rows = (await db.execute(stmt)).all()
    if not rows:
        return []

    card_ids = [c.id for c, _ in rows]
    log_stmt = (
        select(ReviewLog.card_id, ReviewLog.final_grade)
        .where(ReviewLog.card_id.in_(card_ids))
        .order_by(ReviewLog.reviewed_at.asc())
    )
    log_rows = (await db.execute(log_stmt)).all()
    latest_grades: dict[uuid.UUID, str] = dict(log_rows)

    scored_cards: list[tuple[float, Card]] = []
    for card, note in rows:
        fv = note.field_values or {}
        raw_diff = fv.get("difficulty") or fv.get("Difficulty") or fv.get("diff")

        if isinstance(raw_diff, str) and raw_diff.strip():
            d_lower = raw_diff.strip().lower()
            if "easy" in d_lower:
                base_diff = 2.0
            elif "hard" in d_lower:
                base_diff = 8.0
            elif "medium" in d_lower:
                base_diff = 5.0
            else:
                base_diff = 4.5
        elif card.difficulty is not None:
            base_diff = float(card.difficulty)
        else:
            base_diff = 4.0

        if card.difficulty is not None:
            base_diff = (base_diff + float(card.difficulty)) / 2.0

        grade = latest_grades.get(card.id)
        if grade == "easy":
            base_diff -= 1.5
        elif grade == "good":
            base_diff -= 0.5
        elif grade == "hard":
            base_diff += 1.5
        elif grade == "again":
            base_diff += 2.5

        if card.lapse_count:
            base_diff += min(3.0, card.lapse_count * 0.4)
        if card.leech_flag:
            base_diff += 2.5

        scored_cards.append((base_diff, card))

    # Sort ascending: lowest difficulty score first (easiest), highest last (hardest)
    scored_cards.sort(key=lambda x: (x[0], x[1].id))
    cards = [c for _, c in scored_cards]

    items = [_card_item(c, float(c.effective_priority), 12.0) for c in cards]
    await attach_references(db, items)
    return items

