"""APScheduler wiring for the background jobs (§6)."""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.jobs.cache_eviction import evict_stale_cache, release_next_extracts
from app.jobs.optimize_fsrs import run_for_all_users

log = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None


def start() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    sched = AsyncIOScheduler(timezone="UTC")
    sched.add_job(run_for_all_users, CronTrigger(hour=3, minute=30, timezone="UTC"), id="fsrs_optimize")
    sched.add_job(evict_stale_cache, CronTrigger(hour=4, minute=0, timezone="UTC"), id="cache_eviction")
    sched.add_job(release_next_extracts, IntervalTrigger(minutes=30, timezone="UTC"), id="ir_release")
    sched.start()
    _scheduler = sched
    log.info("background jobs started: %s", [j.id for j in sched.get_jobs()])
    return sched


def shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
