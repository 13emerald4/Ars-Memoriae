"""Note-type rendering — Anki-style note/card separation (§2).

One note generates N cards. A Basic note makes one card; a Cloze note makes one
card per distinct ``{{cN::...}}`` index, each scheduling independently. Renderers
are registered on the ``renderer`` seam (§12).
"""

from __future__ import annotations

import re

from app.services import registry

CLOZE_RE = re.compile(r"\{\{c(\d+)::(.+?)(?:::(.+?))?\}\}", re.S)


def cloze_indices(text: str) -> list[int]:
    return sorted({int(m.group(1)) for m in CLOZE_RE.finditer(text or "")})


def render_basic(fields: dict, slot: str) -> tuple[str, str]:
    front = str(fields.get("Front", "") or fields.get("front", ""))
    back = str(fields.get("Back", "") or fields.get("back", ""))
    # "t1" is the second template of a multi-template note type — Anki's
    # "Basic (and reversed card)" and friends, which arrive via .apkg import.
    if slot in ("t1", "reverse"):
        return back, front
    return front, back


def render_cloze(fields: dict, slot: str) -> tuple[str, str]:
    """``slot`` is "c1", "c2", … — the deletion this card tests."""
    text = str(fields.get("Text", "") or fields.get("text", ""))
    extra = str(fields.get("Extra", "") or fields.get("extra", ""))
    try:
        target = int(slot.lstrip("c"))
    except ValueError:
        target = 1

    answers: list[str] = []

    def sub(m: re.Match) -> str:
        idx, content, hint = int(m.group(1)), m.group(2), m.group(3)
        if idx == target:
            answers.append(content)
            return f"[{hint}]" if hint else "[…]"
        return content  # other deletions are shown as context

    front = CLOZE_RE.sub(sub, text)
    back = ", ".join(answers) if answers else CLOZE_RE.sub(lambda m: m.group(2), text)
    if extra:
        back = f"{back}\n\n{extra}"
    return front, back


def shapes_of(fields: dict) -> list[dict]:
    """Occlusion regions, stored as fractions of the image (0-1) so a mask
    lands in the same place at any render size."""
    raw = fields.get("Shapes") or fields.get("shapes") or []
    if not isinstance(raw, list):
        return []
    out = []
    for i, shape in enumerate(raw):
        if not isinstance(shape, dict):
            continue
        try:
            x, y, w, h = (float(shape[k]) for k in ("x", "y", "w", "h"))
        except (KeyError, TypeError, ValueError):
            continue
        if w <= 0 or h <= 0:
            continue
        out.append(
            {
                "id": str(shape.get("id") or f"o{i + 1}"),
                "x": max(0.0, min(1.0, x)),
                "y": max(0.0, min(1.0, y)),
                "w": max(0.0, min(1.0, w)),
                "h": max(0.0, min(1.0, h)),
                "label": str(shape.get("label") or ""),
            }
        )
    return out


def render_image_occlusion(fields: dict, slot: str) -> tuple[str, str]:
    """Text rendering of one occlusion card (§14 Phase 4).

    The *visual* card is drawn by the frontend from ``occlusion_payload``; this
    text form is what browse, export, and LLM grading see. A region with a
    label is gradeable like any short-answer card; an unlabelled one is a
    reveal-only card, which is stated rather than left blank.
    """
    header = str(fields.get("Header", "") or fields.get("Front", "")).strip()
    extra = str(fields.get("Back Extra", "") or fields.get("Back", "")).strip()
    shapes = shapes_of(fields)
    target = next((s for s in shapes if s["id"] == slot), None)

    if target is None:
        # An imported Anki occlusion note whose masks we couldn't parse.
        return header or "(image occlusion)", extra

    position = f"region {slot} ({round(target['x'] * 100)}%, {round(target['y'] * 100)}%)"
    front = f"{header}\n\nWhat is hidden at {position}?".strip()
    back = target["label"] or "(no label — reveal only)"
    if extra:
        back = f"{back}\n\n{extra}"
    return front, back


def occlusion_payload(fields: dict, slot: str) -> dict | None:
    """Structured data the review UI needs to draw the masked image."""
    image = str(fields.get("Image", "") or fields.get("image", "")).strip()
    shapes = shapes_of(fields)
    if not image or not shapes:
        return None
    return {
        "image": image,
        "shapes": shapes,
        "target": slot,
        "header": str(fields.get("Header", "") or "").strip(),
    }


registry.register("renderer", "basic", render_basic, default=True)
registry.register("renderer", "cloze", render_cloze)
registry.register("renderer", "image_occlusion", render_image_occlusion)


def render(template_kind: str, fields: dict, slot: str = "default") -> tuple[str, str]:
    """Returns ``(front, back)`` for one card."""
    return registry.get("renderer", template_kind)(fields, slot)


def slots_for(template_kind: str, fields: dict) -> list[str]:
    """Which cards a note generates."""
    if template_kind == "cloze":
        text = str(fields.get("Text", "") or fields.get("text", ""))
        idx = cloze_indices(text)
        return [f"c{i}" for i in idx] or ["c1"]
    if template_kind == "image_occlusion":
        # One independently scheduled card per masked region.
        return [s["id"] for s in shapes_of(fields)] or ["default"]
    return ["default"]


def select_grading_profile(note_type_profile: str, template_kind: str) -> str:
    """The grading-profile seam (§4.5, §12) — the easiest one to make
    externally pluggable first (§14.1 Phase 3)."""
    return registry.get("grading_profile_selector")(note_type_profile, template_kind)


def _default_profile_selector(note_type_profile: str, template_kind: str) -> str:
    return note_type_profile or "short_answer"


registry.register("grading_profile_selector", "note_type", _default_profile_selector, default=True)
