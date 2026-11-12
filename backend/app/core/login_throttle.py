"""Brute-force brake for POST /api/auth/login.

Failures are counted per (client IP, email). After FREE_ATTEMPTS failures in a
row, that pair is locked out for a window that doubles with each further
failure, up to MAX_LOCK_SECONDS. A success clears the count.

A second, much higher ceiling counts failures per email across *all*
addresses. The per-address key can be dodged by a caller who can vary the
address the server sees (a forwarding header through a local proxy); this one
cannot, and it is set high enough that ordinary typos never reach it.

In-memory on purpose: the app runs as a single process, and a restart
forgetting the counts costs an attacker nothing they couldn't get by waiting.
"""

from __future__ import annotations

import time

from fastapi import Request

FREE_ATTEMPTS = 5
BASE_LOCK_SECONDS = 30.0
MAX_LOCK_SECONDS = 15 * 60.0
_MAX_TRACKED = 10_000
# Failures for one email from any address before that email is locked.
EMAIL_FREE_ATTEMPTS = 40
# Stands in for "any address" in the key.
_ANY = "*"

# (ip, email) -> (consecutive failures, locked until [monotonic seconds])
_failures: dict[tuple[str, str], tuple[int, float]] = {}

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def _now() -> float:
    return time.monotonic()


def client_ip(request: Request) -> str:
    """The caller's address. Behind the Cloudflare tunnel every request
    arrives from loopback, so there (and only there, where the header can't
    come from an outside client directly) the forwarded address is used."""
    host = request.client.host if request.client else "unknown"
    if host in _LOOPBACK:
        forwarded = request.headers.get("cf-connecting-ip")
        if forwarded:
            return forwarded.strip()
    return host


def retry_after(ip: str, email: str) -> int:
    """Seconds until this pair may try again; 0 if it may try now."""
    now = _now()
    wait = 0.0
    for key in ((ip, email), (_ANY, email)):
        entry = _failures.get(key)
        if entry is not None:
            wait = max(wait, entry[1] - now)
    return max(0, int(wait + 0.999)) if wait > 0 else 0


def _evict() -> None:
    """Make room without forgetting active lockouts: drop expired entries
    first, then the oldest half. Clearing everything would let a flood of
    junk emails wipe a real lockout."""
    now = _now()
    for key in [k for k, (_, until) in _failures.items() if until <= now]:
        del _failures[key]
    if len(_failures) >= _MAX_TRACKED:
        for key in list(_failures)[: len(_failures) // 2]:
            del _failures[key]


def _bump(key: tuple[str, str], free_attempts: int) -> None:
    count = _failures.pop(key, (0, 0.0))[0] + 1
    locked_until = 0.0
    if count >= free_attempts:
        lock = min(MAX_LOCK_SECONDS, BASE_LOCK_SECONDS * 2 ** (count - free_attempts))
        locked_until = _now() + lock
    # Re-inserted at the end, so dict order doubles as recency for _evict.
    _failures[key] = (count, locked_until)


def record_failure(ip: str, email: str) -> None:
    if len(_failures) >= _MAX_TRACKED:
        _evict()
    _bump((ip, email), FREE_ATTEMPTS)
    _bump((_ANY, email), EMAIL_FREE_ATTEMPTS)


def record_success(ip: str, email: str) -> None:
    _failures.pop((ip, email), None)
    _failures.pop((_ANY, email), None)


def reset() -> None:
    _failures.clear()
