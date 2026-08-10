"""Example plugin — the grading-profile seam (§12, §4.5).

Copy this directory somewhere, point PLUGIN_DIR at it, and restart the backend:

    PLUGIN_DIR=/srv/plugins docker compose up

This one changes *which rubric* the LLM grades with: any note type whose
selected profile is short-answer, but whose content is cloze, is graded as
conceptual instead — on the theory that cloze deletions carved out of prose
usually want partial credit rather than exact-term matching.

A plugin exports ``setup(api)`` and calls ``api["register"](seam, name, impl,
default=True)``. Registering with ``default=True`` makes it the implementation
the app resolves, replacing the first-party one; without it the strategy is
registered but not selected.

Available seams: grading_profile_selector, renderer, queue_composer.
"""


def choose_profile(note_type_profile: str, template_kind: str) -> str:
    if template_kind == "cloze" and note_type_profile == "short_answer":
        return "conceptual"
    return note_type_profile or "short_answer"


def setup(api) -> None:
    api["register"]("grading_profile_selector", "cloze_as_conceptual", choose_profile, default=True)
