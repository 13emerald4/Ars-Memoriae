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


def is_local_request(request: Request) -> bool:
    """True only when the caller is on this machine.

    A loopback socket with forwarding headers is a proxied request. Clients can
    prepend their own entries to X-Forwarded-For (proxies append), so every
    listed address must be loopback, not just the first.
    """
    host = request.client.host if request.client else ""
    if host not in LOOPBACK:
        return False
    return all(addr in LOOPBACK for addr in _forwarded_addresses(request))
