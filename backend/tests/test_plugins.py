"""Externally-loadable plugins (§12, Phase 3 item 5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services import plugins, registry
from app.services.rendering import select_grading_profile


@pytest.fixture
def clean_registry():
    """Snapshot and restore the seams so a plugin test can't leak into others."""
    import copy

    saved = copy.deepcopy(registry._REGISTRY)
    saved_defaults = dict(registry._DEFAULTS)
    saved_loaded = plugins.loaded()
    yield
    registry._REGISTRY.clear()
    registry._REGISTRY.update(saved)
    registry._DEFAULTS.clear()
    registry._DEFAULTS.update(saved_defaults)
    plugins._loaded = saved_loaded


def write_plugin(directory: Path, name: str, body: str) -> Path:
    path = directory / f"{name}.py"
    path.write_text(body, encoding="utf-8")
    return path


def test_disabled_by_default(clean_registry):
    """No PLUGIN_DIR means nothing is loaded — a hosted instance stays closed."""
    assert plugins.load_all("") == []
    assert plugins.load_all(None) == []


def test_missing_directory_is_not_fatal(clean_registry, tmp_path):
    assert plugins.load_all(str(tmp_path / "nope")) == []


def test_plugin_overrides_the_grading_profile_seam(clean_registry, tmp_path):
    write_plugin(
        tmp_path,
        "cloze_conceptual",
        '''
def choose(note_type_profile, template_kind):
    if template_kind == "cloze" and note_type_profile == "short_answer":
        return "conceptual"
    return note_type_profile


def setup(api):
    api["register"]("grading_profile_selector", "test_override", choose, default=True)
''',
    )
    # Before: the first-party selector just echoes the note type's profile.
    assert select_grading_profile("short_answer", "cloze") == "short_answer"

    loaded = plugins.load_all(str(tmp_path))
    assert len(loaded) == 1
    assert loaded[0].error is None
    assert loaded[0].registered == ["grading_profile_selector:test_override"]

    # After: the plugin's strategy is what the app resolves.
    assert select_grading_profile("short_answer", "cloze") == "conceptual"
    assert select_grading_profile("math_code", "basic") == "math_code"


def test_registering_without_default_does_not_take_over(clean_registry, tmp_path):
    write_plugin(
        tmp_path,
        "optional",
        '''
def setup(api):
    api["register"]("grading_profile_selector", "unused", lambda p, k: "math_code")
''',
    )
    plugins.load_all(str(tmp_path))
    assert "unused" in registry.available("grading_profile_selector")
    assert select_grading_profile("short_answer", "cloze") == "short_answer"


def test_unknown_seam_is_rejected(clean_registry, tmp_path):
    write_plugin(
        tmp_path,
        "typo",
        '''
def setup(api):
    api["register"]("gradingprofile", "oops", lambda *a: "x", default=True)
''',
    )
    loaded = plugins.load_all(str(tmp_path))
    assert loaded[0].error is not None
    assert "not pluggable" in loaded[0].error


def test_non_callable_implementation_is_rejected(clean_registry, tmp_path):
    write_plugin(
        tmp_path,
        "notafunc",
        '''
def setup(api):
    api["register"]("grading_profile_selector", "bad", "not a function", default=True)
''',
    )
    assert "must be callable" in plugins.load_all(str(tmp_path))[0].error


def test_a_broken_plugin_does_not_stop_the_others(clean_registry, tmp_path):
    write_plugin(tmp_path, "aaa_broken", "raise RuntimeError('boom')\n")
    write_plugin(
        tmp_path,
        "zzz_good",
        '''
def setup(api):
    api["register"]("grading_profile_selector", "survivor", lambda p, k: "conceptual", default=True)
''',
    )
    loaded = plugins.load_all(str(tmp_path))
    assert len(loaded) == 2

    broken = next(p for p in loaded if p.name == "aaa_broken")
    good = next(p for p in loaded if p.name == "zzz_good")
    assert "RuntimeError: boom" in broken.error
    assert good.error is None
    assert select_grading_profile("short_answer", "basic") == "conceptual"


def test_plugin_without_setup_is_reported(clean_registry, tmp_path):
    write_plugin(tmp_path, "empty", "X = 1\n")
    loaded = plugins.load_all(str(tmp_path))
    assert "no setup(api) function" in loaded[0].error


def test_underscore_files_are_skipped(clean_registry, tmp_path):
    write_plugin(tmp_path, "_helpers", "raise RuntimeError('should not be imported')\n")
    assert plugins.load_all(str(tmp_path)) == []


def test_shipped_example_plugin_actually_works(clean_registry):
    """The example in plugins.example/ must not rot — it's the documentation."""
    example_dir = Path(__file__).resolve().parents[1] / "plugins.example"
    assert example_dir.is_dir(), "plugins.example/ is referenced by the README"

    loaded = plugins.load_all(str(example_dir))
    assert loaded, "example directory contained no plugins"
    assert all(p.error is None for p in loaded), [p.error for p in loaded]
    assert select_grading_profile("short_answer", "cloze") == "conceptual"


async def test_plugins_endpoint_reports_state(auth_client):
    resp = await auth_client.get("/api/plugins")
    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is False
    assert body["plugin_dir"] is None
    # The seams are advertised even when loading is off, so an operator can see
    # what is pluggable before enabling anything.
    assert "grading_profile_selector" in body["seams"]
    assert "note_type" in body["seams"]["grading_profile_selector"]
