"""Where a request really came from.

Used to decide whether a caller is sitting at this machine. The backend is
often reached through something running on loopback (the Cloudflare tunnel,
the Vite dev proxy), so the socket address alone says nothing: those hops
are only trusted to *add* forwarding headers, never to vouch that a caller is
local.
"""

from __future__ import annotations

from fastapi import Request

LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost", "::ffff:127.0.0.1"})

# Any of these means the request crossed a proxy on its way here.
_FORWARD_HEADERS = ("cf-connecting-ip", "x-forwarded-for", "x-real-ip", "true-client-ip")


def _forwarded_addresses(request: Request) -> list[str]:
    found: list[str] = []
    for name in _FORWARD_HEADERS:
        raw = request.headers.get(name)
        if raw:
            found.extend(part.strip() for part in raw.split(",") if part.strip())
    if request.headers.get("forwarded"):
        # RFC 7239 is not worth parsing here: its presence alone proves a proxy.
        found.append("forwarded")
    return found


def _hostname(value: str) -> str:
    """Host header value without its port: "localhost:8000" -> "localhost",
    "[::1]:8000" -> "::1"."""
    value = value.strip().lower()
    if value.startswith("["):
        return value[1:].split("]", 1)[0]
    return value.rsplit(":", 1)[0] if value.count(":") == 1 else value


def is_local_request(request: Request) -> bool:
    """True only when the caller is on this machine.

    Three things must all hold:

    * the socket is loopback;
    * no forwarding header names a non-loopback address. Clients can prepend
      their own entries to X-Forwarded-For (proxies append), so every listed
      address must be loopback, not just the first;
    * the browser addressed the app by a loopback name. A tunnel delivers
      requests from loopback too, and not every tunnel adds a forwarding
      header, but the Host it passes on is the public one.
    """
    host = request.client.host if request.client else ""
    if host not in LOOPBACK:
        return False
    if not all(addr in LOOPBACK for addr in _forwarded_addresses(request)):
        return False
    for name in ("host", "x-forwarded-host"):
        raw = request.headers.get(name)
        if raw and any(_hostname(part) not in LOOPBACK for part in raw.split(",") if part.strip()):
            return False
    return True
