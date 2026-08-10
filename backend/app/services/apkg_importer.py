"""Anki `.apkg` import (§11) — Phase 1, so existing users don't start from zero.

An `.apkg` is a zip holding a SQLite collection plus media. Two collection
layouts exist in the wild and both are handled:
  * schema 11  — note types and decks live as JSON blobs in the ``col`` row.
  * schema 18  — they live in real ``notetypes`` / ``fields`` / ``templates`` /
    ``decks`` tables, with the interesting bits in protobuf ``config`` blobs we
    deliberately do not parse; names come from the tables and cloze-ness is
    detected from the note text instead. That inference is recorded as a warning.

FSRS state translation (§11): rather than mapping Anki's SM-2 ease/interval
onto D/S with a formula, each card's real review history is *replayed* through
FSRS. That recovers stability/difficulty from the actual data and needs no
torch, so it works on the default image. The optional parameter refit still
runs afterwards when the optimizer extra is installed.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

FIELD_SEP = "\x1f"
ANKI_TYPE_TO_STATE = {0: "new", 1: "learning", 2: "review", 3: "relearning"}
EASE_TO_GRADE = {1: "again", 2: "hard", 3: "good", 4: "easy"}
CLOZE_HINT = re.compile(r"\{\{c\d+::")
IMG_RE = re.compile(r"<img[^>]*\bsrc\s*=\s*[\"']([^\"']+)[\"'][^>]*>", re.I)
SOUND_RE = re.compile(r"\[sound:([^\]]+)\]")
BR_RE = re.compile(r"<\s*(br|/p|/div|/li)\s*/?\s*>", re.I)
TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class ParsedNoteType:
    anki_id: int
    name: str
    is_cloze: bool
    field_names: list[str]
    template_count: int


@dataclass
class ParsedNote:
    anki_id: int
    note_type_id: int
    fields: list[str]
    tags: list[str]


@dataclass
class ParsedCard:
    anki_id: int
    note_id: int
    deck_id: int
    ord: int
    state: str
    interval_days: int
    lapses: int
    due_at: datetime | None
    suspended: bool


@dataclass
class ParsedReview:
    card_id: int
    reviewed_at: datetime
    grade: str
    duration_ms: int | None


@dataclass
class ParsedCollection:
    note_types: dict[int, ParsedNoteType] = field(default_factory=dict)
    decks: dict[int, str] = field(default_factory=dict)
    notes: list[ParsedNote] = field(default_factory=list)
    cards: list[ParsedCard] = field(default_factory=list)
    reviews: list[ParsedReview] = field(default_factory=list)
    media: dict[str, str] = field(default_factory=dict)  # zip member -> filename
    media_dir: Path | None = None
    warnings: list[str] = field(default_factory=list)


class ApkgError(RuntimeError):
    pass


# ── field text handling ─────────────────────────────────────────────────────


def flatten_html(text: str, media_url: dict[str, str] | None = None) -> str:
    """Anki fields are HTML; our template model is plain text (§11).

    Media references are preserved as markdown so images survive the flatten;
    everything else is stripped. Callers record a warning when this actually
    discarded markup.
    """
    media_url = media_url or {}

    def img_sub(m: re.Match) -> str:
        name = html.unescape(m.group(1))
        return f"![]({media_url.get(name, name)})"

    def sound_sub(m: re.Match) -> str:
        name = html.unescape(m.group(1))
        return f"[audio]({media_url.get(name, name)})"

    out = IMG_RE.sub(img_sub, text or "")
    out = SOUND_RE.sub(sound_sub, out)
    out = BR_RE.sub("\n", out)
    out = TAG_RE.sub("", out)
    out = html.unescape(out)
    out = re.sub(r"[ \t]+", " ", out)
    return re.sub(r"\n{3,}", "\n\n", out).strip()


def had_markup(text: str) -> bool:
    return bool(TAG_RE.search(text or ""))


# ── parsing ─────────────────────────────────────────────────────────────────


def _open_collection(zf: zipfile.ZipFile, workdir: Path) -> Path:
    names = set(zf.namelist())
    for candidate in ("collection.anki2", "collection.anki21"):
        if candidate in names:
            target = workdir / candidate
            target.write_bytes(zf.read(candidate))
            # anki21 written by newer clients can still be zstd-framed.
            if target.read_bytes()[:4] == b"\x28\xb5\x2f\xfd":
                continue
            return target
    if "collection.anki21b" in names or "collection.anki21" in names:
        raise ApkgError(
            "This .apkg uses Anki's newer compressed collection format. Re-export "
            "from Anki with “Support older Anki versions” ticked and try again."
        )
    raise ApkgError("no collection.anki2 / collection.anki21 found inside the .apkg")


def _parse_note_types(con: sqlite3.Connection, coll: ParsedCollection) -> None:
    models_json = ""
    try:
        row = con.execute("SELECT models FROM col LIMIT 1").fetchone()
        models_json = row[0] if row else ""
    except sqlite3.Error:
        pass

    if models_json and models_json.strip() not in ("", "{}"):
        for mid, model in json.loads(models_json).items():
            coll.note_types[int(mid)] = ParsedNoteType(
                anki_id=int(mid),
                name=model.get("name", "Imported"),
                is_cloze=int(model.get("type", 0)) == 1,
                field_names=[f.get("name", f"Field{i}") for i, f in enumerate(model.get("flds", []))],
                template_count=max(1, len(model.get("tmpls", []))),
            )
        return

    # Schema 18: names from tables, cloze-ness inferred from note text below.
    try:
        rows = con.execute("SELECT id, name FROM notetypes").fetchall()
    except sqlite3.Error as exc:
        raise ApkgError(f"unrecognised collection schema: {exc}") from exc

    fields_by_nt: dict[int, list[tuple[int, str]]] = {}
    for ntid, ordinal, name in con.execute("SELECT ntid, ord, name FROM fields"):
        fields_by_nt.setdefault(ntid, []).append((ordinal, name))
    tmpl_counts: dict[int, int] = {}
    for ntid, count in con.execute("SELECT ntid, COUNT(*) FROM templates GROUP BY ntid"):
        tmpl_counts[ntid] = count

    for ntid, name in rows:
        names = [n for _, n in sorted(fields_by_nt.get(ntid, []))]
        coll.note_types[int(ntid)] = ParsedNoteType(
            anki_id=int(ntid),
            name=name,
            is_cloze=False,  # refined in _infer_cloze
            field_names=names or ["Front", "Back"],
            template_count=max(1, tmpl_counts.get(ntid, 1)),
        )
    coll.warnings.append(
        "Collection uses Anki's newer schema: note-type templates are stored in a "
        "binary format we do not parse, so card layout was inferred from field "
        "names and cloze markers rather than read from the template definitions."
    )


def _infer_cloze(coll: ParsedCollection) -> None:
    for note in coll.notes:
        nt = coll.note_types.get(note.note_type_id)
        if nt and not nt.is_cloze and any(CLOZE_HINT.search(f) for f in note.fields):
            nt.is_cloze = True


def _parse_decks(con: sqlite3.Connection, coll: ParsedCollection) -> None:
    try:
        row = con.execute("SELECT decks FROM col LIMIT 1").fetchone()
        if row and row[0] and row[0].strip() not in ("", "{}"):
            for did, deck in json.loads(row[0]).items():
                coll.decks[int(did)] = deck.get("name", "Imported")
            return
    except (sqlite3.Error, json.JSONDecodeError):
        pass
    try:
        for did, name in con.execute("SELECT id, name FROM decks"):
            coll.decks[int(did)] = (name or "Imported").replace("\x1f", "::")
    except sqlite3.Error:
        coll.warnings.append("Could not read deck names; everything landed in one deck.")


def parse_apkg(path: Path, workdir: Path) -> ParsedCollection:
    coll = ParsedCollection()
    with zipfile.ZipFile(path) as zf:
        db_path = _open_collection(zf, workdir)

        # media manifest: {"0": "picture.jpg", ...}
        if "media" in zf.namelist():
            try:
                raw = zf.read("media").decode("utf-8", "replace")
                coll.media = dict(json.loads(raw).items()) if raw.strip() else {}
            except (json.JSONDecodeError, UnicodeDecodeError):
                coll.warnings.append("Media manifest was unreadable; media was not imported.")
        if coll.media:
            media_dir = workdir / "media"
            media_dir.mkdir(exist_ok=True)
            for member, filename in coll.media.items():
                if member in zf.namelist():
                    safe = Path(filename).name
                    (media_dir / safe).write_bytes(zf.read(member))
            coll.media_dir = media_dir

    con = sqlite3.connect(db_path)
    try:
        crt_row = con.execute("SELECT crt FROM col LIMIT 1").fetchone()
        crt = datetime.fromtimestamp(crt_row[0], tz=UTC) if crt_row else None

        _parse_note_types(con, coll)
        _parse_decks(con, coll)

        for nid, mid, flds, tags in con.execute("SELECT id, mid, flds, tags FROM notes"):
            coll.notes.append(
                ParsedNote(
                    anki_id=int(nid),
                    note_type_id=int(mid),
                    fields=(flds or "").split(FIELD_SEP),
                    tags=[t for t in (tags or "").split(" ") if t],
                )
            )
        _infer_cloze(coll)

        for cid, nid, did, ordinal, ctype, queue, due, ivl, lapses in con.execute(
            "SELECT id, nid, did, ord, type, queue, due, ivl, lapses FROM cards"
        ):
            state = ANKI_TYPE_TO_STATE.get(int(ctype), "new")
            due_at = None
            if state == "review" and crt is not None:
                # Review-card `due` counts days since collection creation.
                due_at = crt + timedelta(days=int(due))
            elif state in ("learning", "relearning") and int(due) > 1_000_000_000:
                due_at = datetime.fromtimestamp(int(due), tz=UTC)
            coll.cards.append(
                ParsedCard(
                    anki_id=int(cid),
                    note_id=int(nid),
                    deck_id=int(did),
                    ord=int(ordinal),
                    state=state,
                    interval_days=int(ivl or 0),
                    lapses=int(lapses or 0),
                    due_at=due_at,
                    suspended=int(queue) == -1,
                )
            )

        try:
            for rid, cid, ease, time_ms in con.execute(
                "SELECT id, cid, ease, time FROM revlog ORDER BY id"
            ):
                grade = EASE_TO_GRADE.get(int(ease))
                if not grade:
                    continue  # ease 0 = manual reschedule, not a real review
                coll.reviews.append(
                    ParsedReview(
                        card_id=int(cid),
                        reviewed_at=datetime.fromtimestamp(int(rid) / 1000, tz=UTC),
                        grade=grade,
                        duration_ms=int(time_ms) if time_ms else None,
                    )
                )
        except sqlite3.Error:
            coll.warnings.append("No review history found; imported cards start unscheduled.")
    finally:
        con.close()

    return coll


def unpack(upload_path: Path) -> tuple[ParsedCollection, tempfile.TemporaryDirectory]:
    """Parse an uploaded file. The caller owns (and must clean up) the tempdir,
    because parsed media lives inside it until it has been copied out."""
    tmp = tempfile.TemporaryDirectory(prefix="apkg-")
    try:
        coll = parse_apkg(upload_path, Path(tmp.name))
    except Exception:
        tmp.cleanup()
        raise
    return coll, tmp


def copy_media(coll: ParsedCollection, dest_dir: Path) -> dict[str, str]:
    """Copy media out of the tempdir into permanent storage; returns
    {original filename: public URL} for rewriting field references."""
    if not coll.media_dir or not coll.media_dir.exists():
        return {}
    dest_dir.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, str] = {}
    for src in coll.media_dir.iterdir():
        if not src.is_file():
            continue
        shutil.copy2(src, dest_dir / src.name)
        mapping[src.name] = f"/media/{dest_dir.name}/{src.name}"
    return mapping


def cloze_slots(text: str) -> list[str]:
    return sorted({f"c{int(m)}" for m in re.findall(r"\{\{c(\d+)::", text)}) or ["c1"]
