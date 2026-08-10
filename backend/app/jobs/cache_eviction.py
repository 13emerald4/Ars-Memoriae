"""Grading-cache eviction + IR extract staggering (background jobs, §6)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select

from app.db import SessionLocal
from app.models import Extract, GradingCache, Source

log = logging.getLogger(__name__)

CACHE_TTL_DAYS = 30


async def evict_stale_cache() -> int:
    cutoff = datetime.now(UTC) - timedelta(days=CACHE_TTL_DAYS)
    async with SessionLocal() as db:
        result = await db.execute(delete(GradingCache).where(GradingCache.created_at < cutoff))
        await db.commit()
        count = result.rowcount or 0
    log.info("evicted %s stale grading-cache rows", count)
    return count


async def release_next_extracts() -> int:
    """Keep one extract per active source available at a time (§8.4).

    Sources are ingested chunked, with only the first chunk scheduled; as the
    reader works through them this releases the next one, so a 40-chunk article
    trickles into the queue instead of flooding it.
    """
    now = datetime.now(UTC)
    released = 0
    async with SessionLocal() as db:
        sources = (await db.scalars(select(Source).where(Source.status == "active"))).all()
        for source in sources:
            pending_now = await db.scalar(
                select(func.count())
                .select_from(Extract)
                .where(
                    Extract.source_id == source.id,
                    Extract.status == "active",
                    Extract.next_shown_at.isnot(None),
                    Extract.next_shown_at <= now,
                )
            )
            if pending_now:
                continue
            nxt = await db.scalar(
                select(Extract)
                .where(
                    Extract.source_id == source.id,
                    Extract.status == "active",
                    Extract.next_shown_at.is_(None),
                )
                .order_by(Extract.position)
                .limit(1)
            )
            if nxt is not None:
                nxt.next_shown_at = now
                released += 1
        await db.commit()
    if released:
        log.info("released %s next-up IR extracts", released)
    return released
