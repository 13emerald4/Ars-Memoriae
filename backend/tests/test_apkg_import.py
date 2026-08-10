"""Anki .apkg import (§11), against synthetic collections in both schemas."""

from __future__ import annotations

import io
import json
import sqlite3
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

CRT = int(datetime(2024, 1, 1, tzinfo=UTC).timestamp())

SCHEMA_11 = """
CREATE TABLE col (id integer primary key, crt integer, mod integer, scm integer,
  ver integer, dty integer, usn integer, ls integer, conf text, models text,
  decks text, dconf text, tags text);
CREATE TABLE notes (id integer primary key, guid text, mid integer, mod integer,
  usn integer, tags text, flds text, sfld integer, csum integer, flags integer, data text);
CREATE TABLE cards (id integer primary key, nid integer, did integer, ord integer,
  mod integer, usn integer, type integer, queue integer, due integer, ivl integer,
  factor integer, reps integer, lapses integer, left integer, odue integer,
  odid integer, flags integer, data text);
CREATE TABLE revlog (id integer primary key, cid integer, usn integer, ease integer,
  ivl integer, lastIvl integer, factor integer, time integer, type integer);
"""

MODELS = {
    "1000": {
        "id": 1000,
        "name": "Basic",
        "type": 0,
        "flds": [{"name": "Front", "ord": 0}, {"name": "Back", "ord": 1}],
        "tmpls": [{"name": "Card 1"}],
    },
    "2000": {
        "id": 2000,
        "name": "Cloze",
        "type": 1,
        "flds": [{"name": "Text", "ord": 0}, {"name": "Extra", "ord": 1}],
        "tmpls": [{"name": "Cloze"}],
    },
    "3000": {
        "id": 3000,
        "name": "Basic (and reversed card)",
        "type": 0,
        "flds": [{"name": "Front", "ord": 0}, {"name": "Back", "ord": 1}],
        "tmpls": [{"name": "Card 1"}, {"name": "Card 2"}],
    },
}
DECKS = {"1": {"id": 1, "name": "Default"}, "5": {"id": 5, "name": "Spanish::Verbs"}}


def build_apkg(path: Path, *, with_media: bool = False, with_revlog: bool = True) -> Path:
    db = path.parent / "collection.anki2"
    con = sqlite3.connect(db)
    con.executescript(SCHEMA_11)
    con.execute(
        "INSERT INTO col VALUES (1,?,?,?,11,0,0,0,'{}',?,?,'{}','{}')",
        (CRT, int(time.time()), int(time.time()), json.dumps(MODELS), json.dumps(DECKS)),
    )

    sep = "\x1f"
    notes = [
        (1, "g1", 1000, "vocab spanish", f"hablar{sep}to speak"),
        (2, "g2", 2000, "bio", f"The {{{{c1::mitochondrion}}}} is the {{{{c2::powerhouse}}}}.{sep}Cell bio"),
        (3, "g3", 3000, "", f"gato{sep}cat"),
        (4, "g4", 1000, "html", f"<b>bold</b> question<br>line two{sep}<i>answer</i>"),
    ]
    if with_media:
        notes.append((5, "g5", 1000, "", f'Look: <img src="diagram.png">{sep}A diagram'))
    for nid, guid, mid, tags, flds in notes:
        con.execute(
            "INSERT INTO notes VALUES (?,?,?,?,0,?,?,0,0,0,'')",
            (nid, guid, mid, int(time.time()), f" {tags} " if tags else "", flds),
        )

    # (cid, nid, did, ord, type, queue, due, ivl, lapses)
    cards = [
        (10, 1, 5, 0, 2, 2, 400, 21, 2),   # review card, due day 400
        (11, 2, 1, 0, 2, 2, 380, 10, 0),   # cloze c1
        (12, 2, 1, 1, 0, 0, 0, 0, 0),      # cloze c2, still new
        (13, 3, 1, 0, 2, 2, 390, 15, 1),   # forward
        (14, 3, 1, 1, 0, 0, 0, 0, 0),      # reverse, new
        (15, 4, 1, 0, 0, -1, 0, 0, 0),     # suspended new card
    ]
    if with_media:
        cards.append((16, 5, 1, 0, 0, 0, 0, 0, 0))
    for cid, nid, did, ordinal, ctype, queue, due, ivl, lapses in cards:
        con.execute(
            "INSERT INTO cards VALUES (?,?,?,?,?,0,?,?,?,?,2500,5,?,0,0,0,0,'')",
            (cid, nid, did, ordinal, int(time.time()), ctype, queue, due, ivl, lapses),
        )

    if with_revlog:
        base_ms = int(datetime(2025, 6, 1, tzinfo=UTC).timestamp() * 1000)
        day = 86_400_000
        history = [
            (10, 3, 0), (10, 3, 5), (10, 1, 12), (10, 3, 13), (10, 4, 30),
            (11, 3, 1), (11, 3, 8),
            (13, 3, 2), (13, 2, 9), (13, 3, 20),
        ]
        for i, (cid, ease, day_offset) in enumerate(history):
            con.execute(
                "INSERT INTO revlog VALUES (?,?,0,?,0,0,2500,?,1)",
                (base_ms + day_offset * day + i, cid, ease, 4200),
            )

    con.commit()
    con.close()

    apkg = path
    with zipfile.ZipFile(apkg, "w") as zf:
        zf.write(db, "collection.anki2")
        if with_media:
            png = (
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
                b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            zf.writestr("0", png)
            zf.writestr("media", json.dumps({"0": "diagram.png"}))
        else:
            zf.writestr("media", "{}")
    db.unlink()
    return apkg


@pytest.fixture
def apkg_bytes(tmp_path):
    return build_apkg(tmp_path / "deck.apkg").read_bytes()


async def _import(client, data: bytes, name="deck.apkg"):
    return await client.post(
        "/api/import/apkg",
        files={"file": (name, io.BytesIO(data), "application/octet-stream")},
    )


async def test_import_maps_notes_cards_and_decks(auth_client, apkg_bytes):
    resp = await _import(auth_client, apkg_bytes)
    assert resp.status_code == 200, resp.text
    result = resp.json()

    assert result["notes_mapped"] == 4
    assert result["cards_mapped"] == 6
    assert result["review_logs_mapped"] == 10

    decks = {d["name"] for d in (await auth_client.get("/api/decks")).json()}
    assert "Spanish::Verbs" in decks


async def test_review_history_is_replayed_into_fsrs_state(auth_client, apkg_bytes):
    await _import(auth_client, apkg_bytes)
    cards = (await auth_client.get("/api/cards?include_suspended=true&limit=200")).json()

    hablar = next(c for c in cards if "hablar" in c["front"])
    # Five real reviews replayed -> genuine stability/difficulty, not a guess.
    assert hablar["state"] == "review"
    assert hablar["stability"] is not None and hablar["stability"] > 0
    assert 1 <= hablar["difficulty"] <= 10
    assert hablar["due"] is not None
    # The "again" in its history was counted as a lapse by Anki and preserved.
    assert hablar["lapse_count"] == 2


async def test_cloze_notes_split_into_per_deletion_cards(auth_client, apkg_bytes):
    await _import(auth_client, apkg_bytes)
    cards = (await auth_client.get("/api/cards?include_suspended=true&limit=200")).json()
    cloze = [c for c in cards if c["template_slot"].startswith("c")]
    assert sorted(c["template_slot"] for c in cloze) == ["c1", "c2"]

    c1 = next(c for c in cloze if c["template_slot"] == "c1")
    assert "[…]" in c1["front"]
    assert "mitochondrion" in c1["back"]


async def test_reversed_note_type_produces_a_flipped_card(auth_client, apkg_bytes):
    await _import(auth_client, apkg_bytes)
    cards = (await auth_client.get("/api/cards?include_suspended=true&limit=200")).json()
    forward = next(c for c in cards if c["front"] == "gato")
    reverse = next(c for c in cards if c["front"] == "cat")
    assert forward["back"] == "cat"
    assert reverse["back"] == "gato"
    assert reverse["template_slot"] == "t1"


async def test_html_is_flattened_and_reported_as_a_warning(auth_client, apkg_bytes):
    resp = await _import(auth_client, apkg_bytes)
    warnings = resp.json()["warnings"]
    assert any("HTML formatting" in w for w in warnings)

    cards = (await auth_client.get("/api/cards?include_suspended=true&limit=200")).json()
    flattened = next(c for c in cards if "bold" in c["front"])
    assert "<b>" not in flattened["front"]
    assert flattened["front"] == "bold question\nline two"


async def test_suspended_state_is_preserved(auth_client, apkg_bytes):
    await _import(auth_client, apkg_bytes)
    cards = (await auth_client.get("/api/cards?include_suspended=true&limit=200")).json()
    assert next(c for c in cards if "bold" in c["front"])["suspended"] is True

    visible = (await auth_client.get("/api/cards?limit=200")).json()
    assert not any("bold" in c["front"] for c in visible)


async def test_media_is_copied_and_references_rewritten(auth_client, tmp_path):
    data = build_apkg(tmp_path / "media.apkg", with_media=True).read_bytes()
    resp = await _import(auth_client, data, "media.apkg")
    assert resp.json()["media_copied"] == 1

    cards = (await auth_client.get("/api/cards?include_suspended=true&limit=200")).json()
    with_img = next(c for c in cards if "Look:" in c["front"])
    assert "![](/media/" in with_img["front"]
    assert "diagram.png" in with_img["front"]


async def test_collection_without_history_still_imports(auth_client, tmp_path):
    data = build_apkg(tmp_path / "nohist.apkg", with_revlog=False).read_bytes()
    resp = await _import(auth_client, data, "nohist.apkg")
    assert resp.status_code == 200
    assert resp.json()["review_logs_mapped"] == 0
    assert any("No review history" in w for w in resp.json()["warnings"])

    cards = (await auth_client.get("/api/cards?include_suspended=true&limit=200")).json()
    # Due dates survive even though D/S could not be back-filled (§11).
    hablar = next(c for c in cards if "hablar" in c["front"])
    assert hablar["state"] == "review"
    assert hablar["due"] is not None


async def test_imported_cards_enter_the_queue(auth_client, apkg_bytes):
    await _import(auth_client, apkg_bytes)
    await auth_client.patch("/api/me", json={"daily_new_limit": 50, "daily_review_limit": 200})
    session = (await auth_client.get("/api/queue/session")).json()
    assert session["counts"]["due_total"] + session["counts"]["new_total"] > 0


async def test_garbage_upload_is_rejected_cleanly(auth_client):
    resp = await _import(auth_client, b"this is not a zip file at all")
    assert resp.status_code == 422
    assert "could not read" in resp.json()["detail"].lower()


async def test_import_history_is_audited(auth_client, apkg_bytes):
    await _import(auth_client, apkg_bytes)
    history = (await auth_client.get("/api/import/history")).json()
    assert len(history) >= 1
    assert history[0]["filename"] == "deck.apkg"
    assert history[0]["cards_mapped"] == 6


def test_zstd_collections_get_an_actionable_error(tmp_path):
    """Newer Anki exports use a compressed collection we deliberately don't
    parse; the user needs to be told exactly what to do (§11)."""
    from app.services.apkg_importer import ApkgError, parse_apkg

    apkg = tmp_path / "new.apkg"
    with zipfile.ZipFile(apkg, "w") as zf:
        zf.writestr("collection.anki21b", b"\x28\xb5\x2f\xfd" + b"\x00" * 32)
        zf.writestr("media", "{}")

    with pytest.raises(ApkgError) as exc:
        parse_apkg(apkg, tmp_path)
    assert "Support older Anki versions" in str(exc.value)
