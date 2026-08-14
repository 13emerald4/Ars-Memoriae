"""Incremental Reading (§8).

The SuperMemo loop, adapted: import source material, get it resurfaced on a
spaced schedule, carve cards out of it as understanding builds — without the
pressure to finish an article in one sitting.

Extract scheduling is deliberately *lighter* than FSRS (§8.4): an extract is
not a memory item, it is a piece of unread text. It reappears after N days,
its priority decays as it is worked, and it retires when nothing is left.
"""

from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Extract, KnowledgeNode, Source
from app.services import tree_service

DEFAULT_REVISIT_DAYS = 3
PRIORITY_DECAY = 5  # points shed each time an extract is processed
TARGET_CHUNK_CHARS = 1200


class FetchError(RuntimeError):
    pass


MAX_FETCH_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 5
FETCH_TIMEOUT = 20


async def assert_fetchable(url: str) -> None:
    """Reject URLs that would make the server talk to itself or its neighbours.

    ``POST /api/sources`` lets any authenticated user choose a URL the *server*
    then fetches, which is a server-side request forgery primitive unless the
    destination is constrained: cloud metadata endpoints (169.254.169.254) hand
    out credentials, and container-internal services (postgres:5432, the app's
    own API) are reachable by name from inside the network.

    So every hostname is resolved and every resulting address must be publicly
    routable. Operators who *want* intranet fetching can set
    URL_FETCH_ALLOW_PRIVATE=1.
    """
    if not settings.url_fetch_enabled:
        raise FetchError("URL fetching is disabled on this instance; paste the text instead")

    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise FetchError("only http(s) URLs are supported")
    host = parsed.hostname
    if not host:
        raise FetchError("URL has no host")

    if settings.url_fetch_allow_private:
        return

    try:
        infos = await asyncio.to_thread(
            socket.getaddrinfo, host, parsed.port or (443 if parsed.scheme == "https" else 80),
            0, socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise FetchError(f"could not resolve {host}") from exc

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global or ip.is_multicast:
            raise FetchError(
                f"refusing to fetch {host} — it resolves to the non-public address {ip}"
            )


async def fetch_url(url: str) -> tuple[str, str]:
    """Server-side fetch + boilerplate stripping (§8.1). Returns (title, text).

    Redirects are followed by hand so that *every hop* is re-validated: a
    public URL that 302s to the metadata endpoint would otherwise walk straight
    past a check on the original URL. The body is streamed with a hard cap so a
    huge response can't exhaust memory.
    """
    current = url
    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=FETCH_TIMEOUT) as client:
            for _ in range(MAX_REDIRECTS + 1):
                await assert_fetchable(current)
                async with client.stream(
                    "GET", current, headers={"User-Agent": "memorization-app/0.1"}
                ) as resp:
                    if resp.is_redirect:
                        location = resp.headers.get("location")
                        if not location:
                            raise FetchError("redirect without a Location header")
                        current = str(httpx.URL(current).join(location))
                        continue
                    resp.raise_for_status()

                    chunks: list[bytes] = []
                    size = 0
                    async for chunk in resp.aiter_bytes():
                        size += len(chunk)
                        if size > MAX_FETCH_BYTES:
                            raise FetchError(
                                f"page is larger than {MAX_FETCH_BYTES // (1024 * 1024)} MB"
                            )
                        chunks.append(chunk)
                    encoding = resp.encoding or "utf-8"
                    html = b"".join(chunks).decode(encoding, errors="replace")
                    break
            else:
                raise FetchError(f"more than {MAX_REDIRECTS} redirects")
    except httpx.HTTPError as exc:
        raise FetchError(str(exc)) from exc
    return extract_readable(html, fallback_title=url)


def extract_readable(html: str, fallback_title: str = "Untitled") -> tuple[str, str]:
    """Minimal readability pass: drop chrome, keep the densest text block."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else fallback_title

    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]):
        tag.decompose()

    candidates = soup.find_all(["article", "main"]) or [soup.body or soup]
    best = max(candidates, key=lambda t: len(t.get_text(" ", strip=True)))

    blocks: list[str] = []
    for el in best.find_all(["p", "li", "h1", "h2", "h3", "h4", "blockquote", "pre"]):
        text = el.get_text(" ", strip=True)
        if len(text) > 2:
            blocks.append(text)
    text = "\n\n".join(blocks) or best.get_text("\n", strip=True)
    return title or fallback_title, re.sub(r"\n{3,}", "\n\n", text).strip()


def chunk_text(text: str, target: int = TARGET_CHUNK_CHARS) -> list[str]:
    """Split a source into first-pass extracts on paragraph boundaries.

    Paragraphs are packed up to ``target`` chars so an extract is a coherent
    unit of reading rather than an arbitrary slice; an over-long paragraph is
    split on sentence boundaries instead of mid-word.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        if len(para) > target * 1.6:
            if buf:
                chunks.append(buf)
                buf = ""
            sentences = re.split(r"(?<=[.!?])\s+", para)
            cur = ""
            for s in sentences:
                if cur and len(cur) + len(s) + 1 > target:
                    chunks.append(cur.strip())
                    cur = s
                else:
                    cur = f"{cur} {s}".strip()
            if cur:
                chunks.append(cur.strip())
            continue
        if buf and len(buf) + len(para) + 2 > target:
            chunks.append(buf)
            buf = para
        else:
            buf = f"{buf}\n\n{para}".strip()
    if buf:
        chunks.append(buf)
    return chunks or ([text.strip()] if text.strip() else [])


async def create_source(
    db: AsyncSession,
    user_id,
    *,
    title: str,
    raw_text: str,
    url: str | None = None,
    priority: int = 50,
    parent_node_id=None,
    segments: list[tuple[str | None, str]] | None = None,
    for_reading: bool = True,
) -> Source:
    source = Source(
        user_id=user_id,
        title=title[:300],
        raw_text=raw_text,
        url=url,
        priority=priority,
        for_reading=for_reading,
    )
    db.add(source)
    await db.flush()

    # The source becomes a branch of the knowledge tree, with its chunks hanging
    # underneath — so reading material lands in the same hierarchy as the cards
    # it will eventually produce.
    source_node = KnowledgeNode(
        user_id=user_id,
        kind="source",
        title=source.title,
        source_id=source.id,
        priority=priority,
        parent_id=parent_node_id,
    )
    db.add(source_node)
    await db.flush()

    now = datetime.now(UTC)
    # A document upload supplies its own segmentation, because the page or
    # heading a chunk came from is what makes a card's citation usable; pasted
    # text and URLs have no such structure and fall back to length chunking.
    pieces: list[tuple[str | None, str]] = (
        segments if segments is not None else [(None, c) for c in chunk_text(raw_text)]
    )
    for position, (locator, chunk) in enumerate(pieces):
        extract = Extract(
            source_id=source.id,
            content=chunk,
            position=position,
            locator=locator,
            # The first extract is available immediately; later ones are
            # staggered so a 40-chunk article does not flood the queue.
            next_shown_at=now if position == 0 else None,
        )
        db.add(extract)
        await db.flush()
        db.add(
            KnowledgeNode(
                user_id=user_id,
                kind="extract",
                title=tree_service.snippet(chunk),
                extract_id=extract.id,
                parent_id=source_node.id,
                position=position,
            )
        )
    await db.flush()
    return source


async def split_extract(
    db: AsyncSession,
    parent: Extract,
    *,
    text: str | None,
    start: int | None,
    end: int | None,
    priority: int | None,
    remove_from_parent: bool,
    source: Source | None = None,
) -> Extract:
    """Carve a smaller extract out of a larger one — the core SuperMemo loop:
    read a bit, extract the important sub-part, postpone the rest (§8.2).

    The child is filed *beneath the parent* in the knowledge tree. That lineage
    is the point of the loop and it used to be discarded: both fragments landed
    as siblings under the source, so after a few passes you could no longer see
    which idea came out of which passage.
    """
    content = parent.content
    if text:
        fragment = text.strip()
        idx = content.find(fragment)
    elif start is not None and end is not None and 0 <= start < end <= len(content):
        fragment = content[start:end].strip()
        idx = start
    else:
        raise ValueError("provide either `text` or a valid `start`/`end` span")

    if not fragment:
        raise ValueError("empty selection")

    child = Extract(
        source_id=parent.source_id,
        content=fragment,
        priority=priority if priority is not None else parent.priority,
        position=parent.position,
        next_shown_at=datetime.now(UTC),
    )
    db.add(child)
    await db.flush()

    if source is not None:
        parent_node = await tree_service.ensure_extract_node(db, source.user_id, parent, source)
        db.add(
            KnowledgeNode(
                user_id=source.user_id,
                kind="extract",
                title=tree_service.snippet(fragment),
                extract_id=child.id,
                parent_id=parent_node.id,
                position=parent.position,
            )
        )

    if remove_from_parent and idx >= 0:
        remainder = (content[:idx] + content[idx + len(fragment) :]).strip()
        remainder = re.sub(r"\n{3,}", "\n\n", remainder)
        if remainder:
            parent.content = remainder
        else:
            # Nothing unprocessed left — the parent retires (§8.4).
            parent.status = "done"

    await db.flush()
    return child


def postpone(extract: Extract, days: int | None = None, *, inherited_priority: int = 50) -> None:
    """Resurface later, shedding a little priority each pass (§8.4).

    A fresh extract stores NULL priority, meaning "inherit the source". The
    decay has to materialize that inherited value first, or every extract that
    has never been re-prioritised would silently never decay.
    """
    delay = DEFAULT_REVISIT_DAYS if days is None else days
    extract.next_shown_at = datetime.now(UTC) + timedelta(days=delay)
    base = extract.priority if extract.priority is not None else inherited_priority
    extract.priority = max(0, base - PRIORITY_DECAY)


async def source_progress(db: AsyncSession, source_id) -> tuple[int, int]:
    total = await db.scalar(
        select(func.count()).select_from(Extract).where(Extract.source_id == source_id)
    )
    active = await db.scalar(
        select(func.count())
        .select_from(Extract)
        .where(Extract.source_id == source_id, Extract.status == "active")
    )
    return int(total or 0), int(active or 0)


async def retire_if_complete(db: AsyncSession, source: Source) -> None:
    _, active = await source_progress(db, source.id)
    if active == 0 and source.status == "active":
        source.status = "done"
