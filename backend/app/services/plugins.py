"""Externally-loadable plugins (§12, Phase 3 item 5).

Phase 1 built the seams — note-type rendering, grading-profile selection, and
queue composition are resolved through ``registry`` rather than called
directly. This is the first one that outside code can actually plug into.

§12 leaves the mechanism open between a sandboxed Python entry-point system
and a webhook model, deliberately not locking it in early. This picks the
Python one, for a narrow reason: the app's first-class deployment target is
self-hosting (§10), where "sandboxed" would be security theatre — the operator
already controls the container, the database, and the secrets. So plugins here
are **trusted local code**, not untrusted uploads:

  * loading is OFF unless PLUGIN_DIR is set,
  * plugins are plain .py files read from that directory on the local disk,
  * they run with the backend's full privileges, and the loader says so.

A multi-tenant hosted instance must leave PLUGIN_DIR unset; a webhook model is
the right answer there and can register through the same seams later without
changing a single call site. That is the whole point of having built the seams
first.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import settings
from app.services import registry

log = logging.getLogger(__name__)

# What a plugin module may touch. Anything else it registers is rejected, so a
# typo in a seam name fails loudly at load instead of silently doing nothing.
ALLOWED_SEAMS = {"grading_profile_selector", "renderer", "queue_composer"}


@dataclass
class LoadedPlugin:
    name: str
    path: str
    registered: list[str] = field(default_factory=list)
    error: str | None = None


_loaded: list[LoadedPlugin] = []


def loaded() -> list[LoadedPlugin]:
    return list(_loaded)


def plugin_api() -> dict:
    """The surface a plugin module is handed. Deliberately tiny — one verb."""
    return {"register": _guarded_register}


def _guarded_register(seam: str, name: str, impl, *, default: bool = False) -> None:
    if seam not in ALLOWED_SEAMS:
        raise ValueError(
            f"seam {seam!r} is not pluggable; available: {sorted(ALLOWED_SEAMS)}"
        )
    if not callable(impl):
        raise TypeError(f"implementation for {seam}/{name} must be callable")
    registry.register(seam, name, impl, default=default)


def load_all(directory: str | None = None) -> list[LoadedPlugin]:
    """Import every ``*.py`` in the plugin directory, newest registration wins.

    One broken plugin must not take the server down: each is loaded in its own
    try block and a failure is recorded and surfaced via GET /api/plugins.
    """
    global _loaded
    _loaded = []

    target = directory or settings.plugin_dir
    if not target:
        return _loaded

    root = Path(target)
    if not root.is_dir():
        log.warning("PLUGIN_DIR %s does not exist; no plugins loaded", root)
        return _loaded

    log.warning(
        "Loading plugins from %s — plugin code runs with full backend privileges. "
        "Do not enable PLUGIN_DIR on a shared/multi-tenant instance.",
        root,
    )

    for path in sorted(root.glob("*.py")):
        if path.name.startswith("_"):
            continue
        record = LoadedPlugin(name=path.stem, path=str(path))
        before = {seam: set(registry.available(seam)) for seam in ALLOWED_SEAMS}
        try:
            module = _import_file(path)
            setup = getattr(module, "setup", None)
            if callable(setup):
                setup(plugin_api())
            elif not any(
                set(registry.available(seam)) - before[seam] for seam in ALLOWED_SEAMS
            ):
                raise AttributeError(
                    "plugin defines no setup(api) function and registered nothing at import"
                )
            for seam in ALLOWED_SEAMS:
                for added in sorted(set(registry.available(seam)) - before[seam]):
                    record.registered.append(f"{seam}:{added}")
        except Exception as exc:
            record.error = f"{type(exc).__name__}: {exc}"
            log.exception("plugin %s failed to load", path.name)
        _loaded.append(record)

    ok = sum(1 for p in _loaded if not p.error)
    log.info("loaded %s/%s plugins", ok, len(_loaded))
    return _loaded


def _import_file(path: Path):
    module_name = f"memorization_plugin_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build an import spec for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module
