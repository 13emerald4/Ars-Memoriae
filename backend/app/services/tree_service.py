"""The knowledge tree — one hierarchy over decks, sources and extracts.

SuperMemo organises everything you are learning as a single tree: branches for
subjects, articles hanging inside them, extracts hanging inside *those*, and
items at the leaves. Priority flows down a branch, and you can study one branch
instead of the whole collection.

This app already had the pieces but in two disconnected shapes — a deck tree
holding only cards, and a flat source list holding only reading material. This
module is the tree that spans both.

Two decisions worth stating:

**The tree overlays the entities, it doesn't replace them.** A node points at
the deck / source / extract it stands for; a ``topic`` node points at nothing
and exists purely to group. Nothing about scheduling changed: the composer
still reads ``Card.priority`` / ``Deck.default_priority`` exactly as before, so
there is one number the scheduler can see, not two competing ones. What the
tree adds is a way to *write* that number down an entire branch at once
(:func:`set_priority`) and a way to scope a session to a branch
(:func:`branch_scope`).

**Structure is walked in Python, not in a recursive CTE.** The walk is bounded
by node count — decks, sources and extracts — which is orders of magnitude
smaller than card count and is the same set the tree view has to render
anyway. One narrow indexed query per operation beats a CTE whose behaviour we'd
have to verify separately on SQLite and Postgres.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Card, Deck, Extract, KnowledgeNode, Note, Source, User

DEFAULT_PRIORITY = 50
TITLE_CHARS = 80


class TreeError(ValueError):
    """A structural operation the tree refuses (cycles, bad parents)."""


def snippet(text: str, limit: int = TITLE_CHARS) -> str:
    flat = " ".join((text or "").split())
    if len(flat) <= limit:
        return flat or "(empty extract)"
    return flat[: limit - 1].rstrip() + "…"


# ── loading & walking ───────────────────────────────────────────────────────


async def load_nodes(db: AsyncSession, user: User) -> list[KnowledgeNode]:
    return list(
        (
            await db.scalars(
                select(KnowledgeNode)
                .where(KnowledgeNode.user_id == user.id)
                .order_by(KnowledgeNode.position, KnowledgeNode.title)
            )
        ).all()
    )


def children_of(nodes: list[KnowledgeNode]) -> dict[uuid.UUID | None, list[KnowledgeNode]]:
    out: dict[uuid.UUID | None, list[KnowledgeNode]] = defaultdict(list)
    for n in nodes:
        out[n.parent_id].append(n)
    for group in out.values():
        group.sort(key=lambda n: (n.position, n.title.lower()))
    return out


def subtree(nodes: list[KnowledgeNode], root_id: uuid.UUID) -> list[KnowledgeNode]:
    """The root plus every descendant, breadth-first.

    Guards against a cycle in the stored rows (which the move check prevents,
    but a hand-edited database could still contain) by never visiting an id
    twice — a cycle would otherwise hang the request.
    """
    kids = children_of(nodes)
    by_id = {n.id: n for n in nodes}
    root = by_id.get(root_id)
    if root is None:
        return []
    out: list[KnowledgeNode] = []
    seen: set[uuid.UUID] = set()
    queue = [root]
    while queue:
        node = queue.pop(0)
        if node.id in seen:
            continue
        seen.add(node.id)
        out.append(node)
        queue.extend(kids.get(node.id, []))
    return out


def ancestors(nodes: list[KnowledgeNode], node: KnowledgeNode) -> list[KnowledgeNode]:
    """Nearest parent first, up to the root."""
    by_id = {n.id: n for n in nodes}
    out: list[KnowledgeNode] = []
    seen: set[uuid.UUID] = {node.id}
    cur = by_id.get(node.parent_id) if node.parent_id else None
    while cur is not None and cur.id not in seen:
        seen.add(cur.id)
        out.append(cur)
        cur = by_id.get(cur.parent_id) if cur.parent_id else None
    return out


def resolve_priority(nodes: list[KnowledgeNode], node: KnowledgeNode) -> tuple[int, bool]:
    """(priority, inherited?) — the nearest ancestor-or-self that declares one."""
    if node.priority is not None:
        return node.priority, False
    for parent in ancestors(nodes, node):
        if parent.priority is not None:
            return parent.priority, True
    return DEFAULT_PRIORITY, True


# ── backfill ────────────────────────────────────────────────────────────────


async def ensure_tree(db: AsyncSession, user: User) -> list[KnowledgeNode]:
    """Give every deck, source and extract a node. Idempotent.

    Runs lazily on read rather than as a one-shot data migration, because rows
    keep arriving from paths that know nothing about the tree — an Anki import
    creating forty decks, say. Reconciling on read means those show up without
    every writer having to remember to call us.

    Existing *extract* lineage cannot be recovered: splitting used to leave no
    record of which extract a fragment came from, so pre-existing extracts all
    land directly under their source. Splits made from now on nest properly.
    """
    nodes = await load_nodes(db, user)
    have_deck = {n.deck_id for n in nodes if n.deck_id}
    have_source = {n.source_id for n in nodes if n.source_id}
    have_extract = {n.extract_id for n in nodes if n.extract_id}
    created = False

    # Decks, mirroring Deck.parent_id. Two passes: every deck node must exist
    # before parents can be wired, since a child can precede its parent.
    deck_rows = (
        await db.execute(
            select(Deck.id, Deck.name, Deck.parent_id, Deck.default_priority)
            .where(Deck.user_id == user.id)
            .order_by(Deck.name)
        )
    ).all()
    node_for_deck = {n.deck_id: n for n in nodes if n.deck_id}
    pos = await _next_position(db, user, None)
    for deck_id, name, _parent, priority in deck_rows:
        if deck_id in have_deck:
            continue
        node = KnowledgeNode(
            user_id=user.id,
            kind="deck",
            title=name,
            deck_id=deck_id,
            priority=priority,
            position=pos,
        )
        db.add(node)
        node_for_deck[deck_id] = node
        pos += 1
        created = True
    if created:
        await db.flush()
    for deck_id, _name, parent_deck_id, _priority in deck_rows:
        node = node_for_deck.get(deck_id)
        parent_node = node_for_deck.get(parent_deck_id) if parent_deck_id else None
        if node is not None and parent_node is not None and node.parent_id is None:
            node.parent_id = parent_node.id

    # Sources at the root; their extracts underneath.
    source_rows = (
        await db.execute(
            select(Source.id, Source.title, Source.priority)
            .where(Source.user_id == user.id)
            .order_by(Source.created_at)
        )
    ).all()
    node_for_source = {n.source_id: n for n in nodes if n.source_id}
    for source_id, title, priority in source_rows:
        if source_id in have_source:
            continue
        node = KnowledgeNode(
            user_id=user.id,
            kind="source",
            title=title,
            source_id=source_id,
            priority=priority,
            position=pos,
        )
        db.add(node)
        node_for_source[source_id] = node
        pos += 1
        created = True
    if created:
        await db.flush()

    extract_rows = (
        await db.execute(
            select(
                Extract.id,
                Extract.source_id,
                Extract.position,
                func.substr(Extract.content, 1, TITLE_CHARS * 2),
            )
            .join(Source, Source.id == Extract.source_id)
            .where(Source.user_id == user.id)
            .order_by(Extract.position)
        )
    ).all()
    for extract_id, source_id, position, content in extract_rows:
        if extract_id in have_extract:
            continue
        parent = node_for_source.get(source_id)
        db.add(
            KnowledgeNode(
                user_id=user.id,
                kind="extract",
                title=snippet(content or ""),
                extract_id=extract_id,
                parent_id=parent.id if parent else None,
                position=position,
            )
        )
        created = True

    if created:
        await db.commit()
        return await load_nodes(db, user)
    return nodes


async def ensure_extract_node(
    db: AsyncSession, user_id: uuid.UUID, extract: Extract, source: Source
) -> KnowledgeNode:
    """The node for one extract, creating it (and its source's node) if needed.

    Split needs this: the child has to hang off the parent extract's node, and
    that node may not exist yet if the tree has never been opened.
    """
    node = await db.scalar(select(KnowledgeNode).where(KnowledgeNode.extract_id == extract.id))
    if node is not None:
        return node

    source_node = await db.scalar(select(KnowledgeNode).where(KnowledgeNode.source_id == source.id))
    if source_node is None:
        source_node = KnowledgeNode(
            user_id=user_id,
            kind="source",
            title=source.title,
            source_id=source.id,
            priority=source.priority,
        )
        db.add(source_node)
        await db.flush()

    node = KnowledgeNode(
        user_id=user_id,
        kind="extract",
        title=snippet(extract.content),
        extract_id=extract.id,
        parent_id=source_node.id,
        position=extract.position,
    )
    db.add(node)
    await db.flush()
    return node


async def _next_position(
    db: AsyncSession, user: User | uuid.UUID, parent_id: uuid.UUID | None
) -> int:
    user_id = user.id if isinstance(user, User) else user
    stmt = select(func.max(KnowledgeNode.position)).where(KnowledgeNode.user_id == user_id)
    stmt = stmt.where(
        KnowledgeNode.parent_id.is_(None)
        if parent_id is None
        else KnowledgeNode.parent_id == parent_id
    )
    return int((await db.scalar(stmt)) or 0) + 1


# ── structural operations ───────────────────────────────────────────────────


async def create_topic(
    db: AsyncSession,
    user: User,
    *,
    title: str,
    parent_id: uuid.UUID | None,
    priority: int | None,
) -> KnowledgeNode:
    node = KnowledgeNode(
        user_id=user.id,
        kind="topic",
        title=title.strip() or "Untitled topic",
        parent_id=parent_id,
        priority=priority,
        position=await _next_position(db, user, parent_id),
    )
    db.add(node)
    await db.flush()
    return node


async def move(
    db: AsyncSession,
    user: User,
    node: KnowledgeNode,
    new_parent_id: uuid.UUID | None,
    position: int | None = None,
) -> None:
    """Reparent a node, refusing to build a cycle.

    Moving a branch into its own descendant would orphan the whole thing from
    the root — it would still be in the table but unreachable from any tree
    walk, and :func:`subtree` would loop forever without its seen-set. Cheaper
    to refuse than to detect later.
    """
    if new_parent_id == node.id:
        raise TreeError("a node cannot be its own parent")

    nodes = await load_nodes(db, user)
    if new_parent_id is not None:
        parent = next((n for n in nodes if n.id == new_parent_id), None)
        if parent is None:
            raise TreeError("parent not found")
        if any(n.id == new_parent_id for n in subtree(nodes, node.id)):
            raise TreeError("cannot move a branch inside itself")

    node.parent_id = new_parent_id
    node.position = (
        position if position is not None else await _next_position(db, user, new_parent_id)
    )

    # A deck node's parent is the deck tree's parent too, so the two views can
    # never disagree about deck nesting.
    if node.kind == "deck" and node.deck_id:
        deck = await db.get(Deck, node.deck_id)
        if deck is not None:
            parent_node = (
                next((n for n in nodes if n.id == new_parent_id), None) if new_parent_id else None
            )
            deck.parent_id = (
                parent_node.deck_id if parent_node and parent_node.kind == "deck" else None
            )
            deck.position = node.position
    await db.flush()


async def set_priority(
    db: AsyncSession, user: User, node: KnowledgeNode, priority: int, *, cascade: bool
) -> int:
    """Set a node's priority, optionally writing it through the whole branch.

    Without ``cascade`` this only records the branch's declared priority, which
    descendants inherit for *display*. With it, the number is written onto
    every entity underneath — which is the only thing the scheduler reads, so
    it's what makes "this whole subject matters more" actually change what you
    see. Descendants' own declarations are cleared, so the tree afterwards
    shows one number inherited consistently rather than stale overrides that
    no longer match the entities.

    A card that carries its own explicit priority keeps it: an override set on
    a single card is more specific than a branch-wide sweep.
    """
    node.priority = priority
    touched = 0

    nodes = await load_nodes(db, user)
    targets = subtree(nodes, node.id) if cascade else [node]

    for target in targets:
        if cascade and target.id != node.id:
            target.priority = None
        if target.deck_id:
            deck = await db.get(Deck, target.deck_id)
            if deck is not None:
                deck.default_priority = priority
                touched += 1
        elif target.source_id:
            source = await db.get(Source, target.source_id)
            if source is not None:
                source.priority = priority
                touched += 1
        elif target.extract_id:
            extract = await db.get(Extract, target.extract_id)
            if extract is not None:
                extract.priority = priority
                touched += 1
    await db.flush()
    return touched


async def set_prerequisite(
    db: AsyncSession,
    user: User,
    node: KnowledgeNode,
    requires_node_id: uuid.UUID | None,
    mastery_threshold: int,
) -> None:
    """Gate a node behind another node's mastery, refusing cycles.

    Only topic/deck nodes carry testable content, so only they can be a
    prerequisite or be gated — "90% mastery" doesn't mean anything for a
    reading extract, which has no cards of its own to grade.
    """
    if node.kind not in ("topic", "deck"):
        raise TreeError(f"a {node.kind} node cannot be gated")
    node.mastery_threshold = mastery_threshold

    if requires_node_id is None:
        node.requires_node_id = None
        await db.flush()
        return
    if requires_node_id == node.id:
        raise TreeError("a node cannot require itself")

    nodes = await load_nodes(db, user)
    by_id = {n.id: n for n in nodes}
    target = by_id.get(requires_node_id)
    if target is None:
        raise TreeError("prerequisite not found")
    if target.kind not in ("topic", "deck"):
        raise TreeError(f"a {target.kind} node cannot be a prerequisite")

    # Walk the candidate prerequisite's own chain; if it leads back to `node`,
    # this edge would make a cycle that can never resolve — each side would be
    # waiting on the other to accumulate mastery neither can ever reach.
    seen: set[uuid.UUID] = {node.id}
    cur: KnowledgeNode | None = target
    while cur is not None:
        if cur.id in seen:
            raise TreeError("that would create a prerequisite cycle")
        seen.add(cur.id)
        cur = by_id.get(cur.requires_node_id) if cur.requires_node_id else None

    node.requires_node_id = requires_node_id
    await db.flush()


async def delete_topic(db: AsyncSession, user: User, node: KnowledgeNode) -> int:
    """Remove a grouping node, lifting its children into its parent.

    Deleting a topic must never delete study material — the FK cascade would
    take the whole subtree with it, so children are re-parented first. Nodes
    that stand for an entity aren't deletable here at all; you delete the deck
    or the source, and the node goes with it.
    """
    if node.kind != "topic":
        raise TreeError(
            f"this node is a {node.kind}; delete the {node.kind} itself and its node goes with it"
        )
    kids = list(
        (await db.scalars(select(KnowledgeNode).where(KnowledgeNode.parent_id == node.id))).all()
    )
    for kid in kids:
        kid.parent_id = node.parent_id
    await db.flush()
    await db.delete(node)
    await db.flush()
    return len(kids)


async def detach_entity_node(db: AsyncSession, entity_node_filter) -> None:
    """Lift children out before an entity (and its node) is deleted.

    Called from the deck/source delete paths: without it the node's FK cascade
    would silently take any topics a user had filed underneath it.
    """
    node = await db.scalar(select(KnowledgeNode).where(entity_node_filter))
    if node is None:
        return
    kids = list(
        (await db.scalars(select(KnowledgeNode).where(KnowledgeNode.parent_id == node.id))).all()
    )
    for kid in kids:
        kid.parent_id = node.parent_id
    await db.flush()


async def delete_all_tree(db: AsyncSession, user: User) -> dict[str, int]:
    """Delete all knowledge tree items for the user: sources, extracts, decks, notes, cards, and topics."""
    # 1. Reading sources & extracts
    sources = (await db.scalars(select(Source).where(Source.user_id == user.id))).all()
    source_count = len(sources)
    source_ids = [s.id for s in sources]
    extract_count = 0
    if source_ids:
        extract_ids = (
            await db.scalars(select(Extract.id).where(Extract.source_id.in_(source_ids)))
        ).all()
        extract_count = len(extract_ids)
        if extract_ids:
            for card in (
                await db.scalars(select(Card).where(Card.origin_extract_id.in_(extract_ids)))
            ).all():
                card.origin_extract_id = None
        for source in sources:
            await db.delete(source)

    # 2. Decks, notes, and cards
    deck_ids = (await db.scalars(select(Deck.id).where(Deck.user_id == user.id))).all()
    deck_count = len(deck_ids)
    if deck_ids:
        note_ids = (
            await db.scalars(select(Card.note_id).where(Card.deck_id.in_(deck_ids)).distinct())
        ).all()
        if note_ids:
            notes = (await db.scalars(select(Note).where(Note.id.in_(note_ids)))).all()
            for note in notes:
                await db.delete(note)
        decks = (await db.scalars(select(Deck).where(Deck.id.in_(deck_ids)))).all()
        for deck in decks:
            await db.delete(deck)

    # 3. All remaining knowledge nodes for this user
    nodes = (await db.scalars(select(KnowledgeNode).where(KnowledgeNode.user_id == user.id))).all()
    node_count = len(nodes)
    for node in nodes:
        await db.delete(node)

    await db.commit()
    return {
        "sources": source_count,
        "extracts": extract_count,
        "decks": deck_count,
        "nodes": node_count,
    }


# ── branch scoping ──────────────────────────────────────────────────────────


@dataclass
class BranchScope:
    """Which decks and extracts a branch-scoped session may draw from."""

    node_id: uuid.UUID
    title: str
    deck_ids: set[uuid.UUID] = field(default_factory=set)
    extract_ids: set[uuid.UUID] = field(default_factory=set)

    @property
    def empty(self) -> bool:
        return not self.deck_ids and not self.extract_ids


async def branch_scope(db: AsyncSession, user: User, node_id: uuid.UUID) -> BranchScope | None:
    """Resolve a branch to the entities under it.

    Cards reach the scope two ways: their deck is in the branch, or they were
    carved out of an extract in it (``origin_extract_id``). The second is what
    makes "review this article's branch" mean the cards it produced, not just
    the reading left to do.
    """
    nodes = await load_nodes(db, user)
    root = next((n for n in nodes if n.id == node_id), None)
    if root is None:
        return None
    scope = BranchScope(node_id=node_id, title=root.title)
    for n in subtree(nodes, node_id):
        if n.deck_id:
            scope.deck_ids.add(n.deck_id)
        elif n.extract_id:
            scope.extract_ids.add(n.extract_id)
    return scope


# ── mastery gating (queue-path) ─────────────────────────────────────────────


async def has_any_gating(db: AsyncSession, user: User) -> bool:
    """Whether this user has configured any prerequisite at all.

    Checked first on the queue-composition hot path (§9): the common case is
    no gating configured, and this keeps that case to one indexed existence
    scan rather than paying for mastery computation nobody asked for on every
    single review. Backed by idx_nodes_user_requires (migration 0008).
    """
    return (
        await db.scalar(
            select(KnowledgeNode.id)
            .where(KnowledgeNode.user_id == user.id, KnowledgeNode.requires_node_id.isnot(None))
            .limit(1)
        )
    ) is not None


async def _mastery_counts(
    db: AsyncSession, user: User
) -> tuple[dict[uuid.UUID, int], dict[uuid.UUID, int]]:
    """(total_by_deck, mastered_by_deck) — the minimal query the queue path
    needs. See the is_mastered comment in _own_counts for why "mastered" is
    FSRS's own state == "review" rather than a separate grade-history query:
    same reasoning, kept in sync deliberately rather than shared, because this
    version skips the due/new/extract work _own_counts does for the Tree page
    and that build_tree() needs but the composer never touches.
    """
    is_mastered = case((Card.state == "review", 1), else_=0)
    total_by_deck: dict[uuid.UUID, int] = {}
    mastered_by_deck: dict[uuid.UUID, int] = {}
    rows = await db.execute(
        select(Card.deck_id, func.count(), func.sum(is_mastered))
        .join(Deck, Deck.id == Card.deck_id)
        .where(Deck.user_id == user.id, Card.suspended.is_(False))
        .group_by(Card.deck_id)
    )
    for deck_id, total, mastered in rows.all():
        total_by_deck[deck_id] = int(total or 0)
        mastered_by_deck[deck_id] = int(mastered or 0)
    return total_by_deck, mastered_by_deck


async def locked_entity_ids(db: AsyncSession, user: User) -> tuple[set[uuid.UUID], set[uuid.UUID]]:
    """(locked_deck_ids, locked_source_ids) for the queue composer to exclude.

    Not built on build_tree(): that also computes due/new/extract counts the
    composer has no use for, and this runs after every review. Call
    has_any_gating() first — the no-prerequisites-configured case skips this
    function entirely.

    Locking a topic locks everything filed under it, cards and reading alike:
    "this whole unit is locked" should mean the material behind it too, not
    just the flashcards.
    """
    nodes = await load_nodes(db, user)
    total_by_deck, mastered_by_deck = await _mastery_counts(db, user)

    kids = children_of(nodes)
    mastery_pct: dict[uuid.UUID, int] = {}

    def rollup(node: KnowledgeNode) -> tuple[int, int]:
        mastered = mastered_by_deck.get(node.deck_id, 0) if node.deck_id else 0
        total = total_by_deck.get(node.deck_id, 0) if node.deck_id else 0
        for child in kids.get(node.id, []):
            m, t = rollup(child)
            mastered += m
            total += t
        mastery_pct[node.id] = min(100, round(mastered / total * 100)) if total else 0
        return mastered, total

    for root in kids.get(None, []):
        rollup(root)

    locked_roots = {
        n.id
        for n in nodes
        if n.requires_node_id and mastery_pct.get(n.requires_node_id, 0) < n.mastery_threshold
    }
    locked_ids: set[uuid.UUID] = set()
    for root_id in locked_roots:
        locked_ids.update(n.id for n in subtree(nodes, root_id))

    by_id = {n.id: n for n in nodes}
    locked_deck_ids = {by_id[i].deck_id for i in locked_ids if by_id[i].deck_id}
    locked_source_ids = {by_id[i].source_id for i in locked_ids if by_id[i].source_id}
    return locked_deck_ids, locked_source_ids


# ── read model ──────────────────────────────────────────────────────────────


@dataclass
class NodeCounts:
    cards: int = 0
    due: int = 0
    new: int = 0
    extracts: int = 0
    # Deck-attributed only (see _own_counts) — mastery is a card/deck concept,
    # not something an extract node participates in.
    mastered: int = 0

    def add(self, other: NodeCounts) -> None:
        self.cards += other.cards
        self.due += other.due
        self.new += other.new
        self.extracts += other.extracts
        self.mastered += other.mastered


async def _own_counts(
    db: AsyncSession, user: User, now: datetime
) -> tuple[dict[uuid.UUID, NodeCounts], dict[uuid.UUID, NodeCounts], dict[uuid.UUID, str]]:
    """Counts attributable directly to each deck and each extract.

    Grouped queries rather than per-node ones: a tree with 300 extract nodes
    would otherwise be 300 round trips to render one page.
    """
    by_deck: dict[uuid.UUID, NodeCounts] = defaultdict(NodeCounts)
    by_extract: dict[uuid.UUID, NodeCounts] = defaultdict(NodeCounts)

    # Conditional aggregation, not GROUP BY state/due: grouping on a timestamp
    # would produce a row per distinct due *instant* — tens of thousands of
    # them on an imported collection — to answer a three-number question.
    is_new = case((Card.state == "new", 1), else_=0)
    is_due = case((and_(Card.state != "new", Card.due.isnot(None), Card.due <= now), 1), else_=0)
    # "Mastered" reuses FSRS's own graduation signal (state == "review")
    # rather than re-deriving a parallel one from raw grade history: FSRS
    # already decides "has this been learned enough," it's the same state the
    # rest of the app reads, and it's covered by the state-first composite
    # indexes migration 0003 added — no join, no extra table.
    is_mastered = case((Card.state == "review", 1), else_=0)

    def tally(target: dict[uuid.UUID, NodeCounts], rows, *, with_mastery: bool = False) -> None:
        for row in rows:
            key, total, new_count, due_count = row[:4]
            if key is None:
                continue
            c = target[key]
            c.cards += int(total or 0)
            c.new += int(new_count or 0)
            c.due += int(due_count or 0)
            if with_mastery:
                c.mastered += int(row[4] or 0)

    tally(
        by_deck,
        (
            await db.execute(
                select(
                    Card.deck_id,
                    func.count(),
                    func.sum(is_new),
                    func.sum(is_due),
                    func.sum(is_mastered),
                )
                .join(Deck, Deck.id == Card.deck_id)
                .where(Deck.user_id == user.id, Card.suspended.is_(False))
                .group_by(Card.deck_id)
            )
        ).all(),
        with_mastery=True,
    )

    # Cards carved out of an extract are counted against that extract as well,
    # so an article's branch shows what it has produced. They stay counted in
    # their deck too — the same card genuinely sits in both places in the tree.
    # Mastery is not: gating is a deck/card concept, so an extract's own
    # numbers never carry a mastered count (see NodeCounts).
    tally(
        by_extract,
        (
            await db.execute(
                select(Card.origin_extract_id, func.count(), func.sum(is_new), func.sum(is_due))
                .join(Deck, Deck.id == Card.deck_id)
                .where(
                    Deck.user_id == user.id,
                    Card.suspended.is_(False),
                    Card.origin_extract_id.isnot(None),
                )
                .group_by(Card.origin_extract_id)
            )
        ).all(),
    )

    extract_rows = (
        await db.execute(
            select(
                Extract.id,
                Extract.status,
                func.substr(Extract.content, 1, TITLE_CHARS * 2),
            )
            .join(Source, Source.id == Extract.source_id)
            .where(Source.user_id == user.id)
        )
    ).all()
    titles: dict[uuid.UUID, str] = {}
    for extract_id, status, content in extract_rows:
        titles[extract_id] = snippet(content or "")
        if status == "active":
            by_extract[extract_id].extracts += 1

    return by_deck, by_extract, titles


@dataclass
class TreeNodeView:
    node: KnowledgeNode
    title: str
    priority: int
    priority_inherited: bool
    counts: NodeCounts
    depth: int
    children: list[TreeNodeView] = field(default_factory=list)
    # Mastery gating (§ Learn & Practice sibling feature) — filled in by a
    # second pass over the already-built tree, once every node's rolled-up
    # counts are final. See build_tree.
    mastery_pct: int = 0
    locked: bool = False
    requires_title: str | None = None


def _flatten(views: list[TreeNodeView]) -> list[TreeNodeView]:
    out: list[TreeNodeView] = []
    for v in views:
        out.append(v)
        out.extend(_flatten(v.children))
    return out


def _apply_gating(roots: list[TreeNodeView]) -> None:
    """Resolve mastery_pct and locked across an already-built tree.

    Two passes, deliberately after the tree is fully built rather than woven
    into the bottom-up rollup: a node's prerequisite can be anywhere in the
    tree, not just an ancestor, so its mastery isn't known until *that*
    node's own subtree has finished rolling up. Only once every view has its
    final counts can prerequisites be resolved by simple dict lookup.

    Locking doesn't need to walk the prerequisite chain transitively: a node
    whose prerequisite is itself locked can't have accumulated any reviews
    (its cards were never in the queue), so its own mastery is genuinely
    stuck at 0% and the chain enforces itself through real data rather than
    through extra logic here.
    """
    all_views = _flatten(roots)
    by_id = {v.node.id: v for v in all_views}

    for v in all_views:
        v.mastery_pct = (
            min(100, round(v.counts.mastered / v.counts.cards * 100)) if v.counts.cards else 0
        )

    for v in all_views:
        if v.node.requires_node_id:
            prereq = by_id.get(v.node.requires_node_id)
            v.requires_title = prereq.title if prereq else None
            prereq_pct = prereq.mastery_pct if prereq else 0
            v.locked = prereq_pct < v.node.mastery_threshold

    def propagate(v: TreeNodeView, inherited_lock: bool) -> None:
        v.locked = v.locked or inherited_lock
        for child in v.children:
            propagate(child, v.locked)

    for root in roots:
        propagate(root, False)


async def build_tree(
    db: AsyncSession, user: User, *, now: datetime | None = None
) -> list[TreeNodeView]:
    """The whole tree with rolled-up counts, ready to render."""
    now = now or datetime.now(UTC)
    nodes = await ensure_tree(db, user)
    by_deck, by_extract, extract_titles = await _own_counts(db, user, now)
    kids = children_of(nodes)

    def build(node: KnowledgeNode, depth: int) -> TreeNodeView:
        priority, inherited = resolve_priority(nodes, node)
        title = node.title
        if node.extract_id:
            # Extract text changes when it is split; the stored title is only a
            # fallback for a row the counts query didn't see.
            title = extract_titles.get(node.extract_id, node.title)
        counts = NodeCounts()
        if node.deck_id:
            counts.add(by_deck.get(node.deck_id, NodeCounts()))
        if node.extract_id:
            counts.add(by_extract.get(node.extract_id, NodeCounts()))

        view = TreeNodeView(
            node=node,
            title=title,
            priority=priority,
            priority_inherited=inherited,
            counts=counts,
            depth=depth,
        )
        for child in kids.get(node.id, []):
            child_view = build(child, depth + 1)
            view.children.append(child_view)
            view.counts.add(child_view.counts)
        return view

    roots = [build(n, 0) for n in kids.get(None, [])]
    _apply_gating(roots)
    return roots
