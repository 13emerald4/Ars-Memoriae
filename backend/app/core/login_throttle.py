"""Brute-force brake for POST /api/auth/login.

Failures are counted per (client IP, email). After FREE_ATTEMPTS failures in a
row, that pair is locked out for a window that doubles with each further
failure, up to MAX_LOCK_SECONDS. A success clears the count.

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
    entry = _failures.get((ip, email))
    if entry is None:
        return 0
    return max(0, int(entry[1] - _now() + 0.999))


def record_failure(ip: str, email: str) -> None:
    if len(_failures) >= _MAX_TRACKED:
        now = _now()
        for key in [k for k, (_, until) in _failures.items() if until <= now]:
            del _failures[key]
        if len(_failures) >= _MAX_TRACKED:
            _failures.clear()
    count = _failures.get((ip, email), (0, 0.0))[0] + 1
    locked_until = 0.0
    if count >= FREE_ATTEMPTS:
        lock = min(MAX_LOCK_SECONDS, BASE_LOCK_SECONDS * 2 ** (count - FREE_ATTEMPTS))
        locked_until = _now() + lock
    _failures[(ip, email)] = (count, locked_until)


def record_success(ip: str, email: str) -> None:
    _failures.pop((ip, email), None)


def reset() -> None:
    _failures.clear()
