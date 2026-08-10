"""Internal extension points (§12, Phase 1).

The three seams the spec calls out — note-type rendering, grading-profile
selection, and queue composition — are resolved through this registry rather
than being called directly, so making one externally pluggable later (Phase 3)
is a registration change, not a rewrite of the call sites.

Nothing here is exposed over HTTP yet, and that is deliberate: §12 flags
speculative generality as a real risk, so the registry stays ~60 lines with no
sandboxing, no manifest format, and no loader.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

_REGISTRY: dict[str, dict[str, Callable[..., Any]]] = {
    "renderer": {},
    "grading_profile_selector": {},
    "queue_composer": {},
}

_DEFAULTS: dict[str, str] = {}


def register(seam: str, name: str, impl: Callable[..., Any], *, default: bool = False) -> None:
    if seam not in _REGISTRY:
        raise KeyError(f"unknown extension seam {seam!r}")
    _REGISTRY[seam][name] = impl
    if default or seam not in _DEFAULTS:
        _DEFAULTS[seam] = name


def get(seam: str, name: str | None = None) -> Callable[..., Any]:
    impls = _REGISTRY[seam]
    key = name if name in impls else _DEFAULTS.get(seam)
    if key is None:
        raise LookupError(f"no implementation registered for seam {seam!r}")
    return impls[key]


def available(seam: str) -> list[str]:
    return sorted(_REGISTRY[seam])
