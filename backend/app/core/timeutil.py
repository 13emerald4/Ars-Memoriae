"""The user's study day.

A study day is the user's local calendar day, rolling over at 04:00 rather
than midnight (standard convention), so a late-night session still counts
toward the day it began. Daily caps, heatmaps, and "today" totals all bucket
by this one definition. A user with no timezone set gets UTC.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DAY_ROLLOVER_HOUR = 4


def is_valid_timezone(name: str) -> bool:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return False
    return True


def user_zone(name: str | None) -> tzinfo:
    if name and is_valid_timezone(name):
        return ZoneInfo(name)
    return UTC


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _study_date_local(dt: datetime, zone: tzinfo) -> datetime:
    return _aware(dt).astimezone(zone) - timedelta(hours=DAY_ROLLOVER_HOUR)


def day_start(now: datetime, tz_name: str | None) -> datetime:
    """The UTC instant at which the study day containing `now` began."""
    zone = user_zone(tz_name)
    local = _study_date_local(now, zone)
    start = datetime(local.year, local.month, local.day, DAY_ROLLOVER_HOUR, tzinfo=zone)
    return start.astimezone(UTC)


def day_key(dt: datetime, tz_name: str | None) -> str:
    """ISO date of the study day `dt` falls in, e.g. for heatmap buckets."""
    return _study_date_local(dt, user_zone(tz_name)).date().isoformat()
