"""POST /api/import/apkg, POST /api/import/json (§11)."""

from __future__ import annotations

import asyncio
import logging
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db import get_db
from app.models import (
    Card,
    CardReference,
    Deck,
    Import,
    MediaAsset,
    Note,
    NoteType,
    ReviewLog,
    User,
)
from app.routers.deps import current_user
from app.schemas.core import ImportResult, JsonImportNote, JsonImportRequest, JsonImportResult
from app.services import apkg_importer as apkg
from app.services.fsrs_service import GRADE_TO_RATING, FSRSService
from app.services.note_service import default_note_type, sync_cards

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/import", tags=["import"])

MAX_UPLOAD_BYTES = 512 * 1024 * 1024


@router.post("/apkg", response_model=ImportResult)
async def import_apkg(
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> ImportResult:
    if not (file.filename or "").lower().endswith((".apkg", ".colpkg", ".zip")):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "expected a .apkg file")

    with tempfile.TemporaryDirectory(prefix="apkg-upload-") as upload_dir:
        upload_path = Path(upload_dir) / "collection.apkg"
        size = 0
        with upload_path.open("wb") as fh:
            while chunk := await file.read(1 << 20):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file too large")
                fh.write(chunk)

        # Parsing is sqlite + zip work: keep it off the event loop.
        try:
            coll, tmp = await asyncio.to_thread(apkg.unpack, upload_path)
        except apkg.ApkgError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        except Exception as exc:
            log.exception("apkg parse failed")
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, f"could not read .apkg: {exc}"
            ) from exc

        try:
            result = await _ingest(db, user, coll, file.filename or "collection.apkg")
        finally:
            tmp.cleanup()

    return result


@router.post("/json", response_model=JsonImportResult, status_code=201)
async def import_json(
    body: JsonImportRequest | list[JsonImportNote],
    deck: str | None = Query(
        default=None, max_length=200, description="Deck name — required when the body is a bare array"
    ),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> JsonImportResult:
    """Bulk-create notes/cards from a JSON payload — the non-Anki upload path.

    Accepts either ``{"deck": "...", "notes": [...]}`` or a bare array of
    notes with the deck name given as ``?deck=`` — a plain array is what most
    scripted/LLM flashcard exports actually look like, and there's no reason
    to make every caller hand-wrap one in an envelope first.

    One request targets one deck (created if it doesn't already exist by
    name). A malformed row is skipped and reported in ``warnings`` rather than
    failing the whole batch, mirroring how the .apkg importer handles rows
    that don't map cleanly: a hand-edited JSON file is exactly the case where
    one bad entry in five hundred shouldn't cost you the other 499.

    A note carrying ``quote`` gets a :class:`CardReference` too, which is what
    Learn & Practice needs to teach from. There's no uploaded document behind
    this path to verify the quote against, so it's trusted as given rather
    than checked — the same way ``accept-deck`` trusts an already-verified
    quote.
    """
    if isinstance(body, list):
        deck_name = (deck or "").strip()
        if not deck_name:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "a bare array of notes needs a deck name — pass ?deck=<name>",
            )
        notes, deck_priority = body, None
    else:
        deck_name, notes, deck_priority = body.deck, body.notes, body.priority

    # `JsonImportRequest.notes` already enforces this via Field(), but a bare
    # array bypasses that schema entirely, so it's checked again here.
    if not notes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "at least one note is required")
    if len(notes) > 5000:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "at most 5000 notes per import")

    existing = await db.scalar(select(Deck).where(Deck.user_id == user.id, Deck.name == deck_name))
    deck_created = existing is None
    deck_row = existing or Deck(
        user_id=user.id, name=deck_name, default_priority=deck_priority if deck_priority is not None else 50
    )
    if deck_created:
        db.add(deck_row)
        await db.flush()

    warnings: list[str] = []
    notes_created = 0
    cards_created = 0
    citations_created = 0

    for i, item in enumerate(notes):
        is_cloze = item.kind == "cloze"
        is_code = item.kind == "code" or getattr(item, "card_type", None) == "code" or bool(item.starter_code)
        if is_cloze:
            if not (item.cloze_text or "").strip():
                warnings.append(f"note {i}: kind is \"cloze\" but cloze_text is empty — skipped")
                continue
            field_values = {"Text": item.cloze_text, "Extra": item.back or ""}
        else:
            if not (item.front or "").strip() or not (item.back or "").strip():
                warnings.append(f"note {i}: front and back are both required — skipped")
                continue
            field_values = {"Front": item.front, "Back": item.back}
            if is_code:
                if item.starter_code:
                    field_values["starter_code"] = item.starter_code
                if item.test_cases:
                    field_values["test_cases"] = item.test_cases
                if item.time_complexity:
                    field_values["time_complexity"] = item.time_complexity
                if item.space_complexity:
                    field_values["space_complexity"] = item.space_complexity
                if item.edge_cases:
                    field_values["edge_cases"] = item.edge_cases
                if item.title:
                    field_values["title"] = item.title
                if item.difficulty:
                    field_values["difficulty"] = item.difficulty
                if item.category:
                    field_values["category"] = item.category

        profile = "math_code" if is_code else "short_answer"
        nt = await default_note_type(db, user, "cloze" if is_cloze else "basic", grading_profile=profile)
        note = Note(user_id=user.id, note_type_id=nt.id, field_values=field_values)
        db.add(note)
        await db.flush()

        tags = list(item.tags)
        if is_code:
            if "code" not in tags:
                tags.append("code")
            if item.difficulty and item.difficulty not in tags:
                tags.append(item.difficulty)
            if item.category and item.category not in tags:
                tags.append(item.category)

        cards = await sync_cards(
            db, note, nt, deck_row.id, tags=tags, priority=item.priority, origin="manual"
        )
        notes_created += 1
        cards_created += len(cards)

        quote = (item.quote or "").strip()
        if quote:
            for card in cards:
                db.add(
                    CardReference(
                        card_id=card.id,
                        quote=quote,
                        # Nothing here was extracted from a document we can
                        # check against, so there's no hallucination risk to
                        # flag — the caller supplied this text directly.
                        quote_verified=True,
                        locator=item.locator,
                        source_title=item.source_title,
                    )
                )
                citations_created += 1

    record = Import(
        user_id=user.id,
        filename=f"json:{deck_name}",
        notes_mapped=notes_created,
        cards_mapped=cards_created,
        warnings=warnings,
    )
    db.add(record)
    await db.commit()

    return JsonImportResult(
        deck_id=str(deck_row.id),
        deck_created=deck_created,
        notes_created=notes_created,
        cards_created=cards_created,
        citations_created=citations_created,
        warnings=warnings,
    )


async def _ingest(
    db: AsyncSession, user: User, coll: apkg.ParsedCollection, filename: str
) -> ImportResult:
    warnings = list(coll.warnings)

    media_dest = Path(settings.media_root) / str(user.id)
    media_map = await asyncio.to_thread(apkg.copy_media, coll, media_dest)

    # ── decks ───────────────────────────────────────────────────────────────
    existing_decks = {
        d.name: d for d in (await db.scalars(select(Deck).where(Deck.user_id == user.id))).all()
    }
    deck_map: dict[int, Deck] = {}
    decks_created = 0
    for anki_did, raw_name in (coll.decks or {0: "Imported"}).items():
        name = (raw_name or "Imported").strip() or "Imported"
        deck = existing_decks.get(name)
        if deck is None:
            deck = Deck(user_id=user.id, name=name)
            db.add(deck)
            await db.flush()
            existing_decks[name] = deck
            decks_created += 1
        deck_map[anki_did] = deck
    fallback_deck = next(iter(deck_map.values()), None)
    if fallback_deck is None:
        fallback_deck = Deck(user_id=user.id, name="Imported")
        db.add(fallback_deck)
        await db.flush()
        decks_created += 1

    # ── note types ──────────────────────────────────────────────────────────
    note_type_map: dict[int, NoteType] = {}
    unmapped_templates: list[str] = []
    for anki_mid, nt in coll.note_types.items():
        kind = "cloze" if nt.is_cloze else "basic"
        fields = {"fields": ["Text", "Extra"] if nt.is_cloze else ["Front", "Back"]}
        model = NoteType(
            user_id=user.id,
            name=f"{nt.name} (imported)"[:120],
            template_kind=kind,
            fields=fields,
            # §4.5: imported note types default to short-answer unless the
            # content looks like cloze-heavy long-form material.
            grading_profile="short_answer",
        )
        db.add(model)
        await db.flush()
        note_type_map[anki_mid] = model

        if not nt.is_cloze and nt.template_count > 2:
            unmapped_templates.append(
                f"“{nt.name}” has {nt.template_count} card templates; only the first two "
                "(forward and reverse) map onto our template model."
            )
        if len(nt.field_names) > 2 and not nt.is_cloze:
            unmapped_templates.append(
                f"“{nt.name}” has {len(nt.field_names)} fields "
                f"({', '.join(nt.field_names[:6])}…); extra fields were appended to the back."
            )

    # ── notes ───────────────────────────────────────────────────────────────
    note_map: dict[int, Note] = {}
    note_type_of: dict[int, apkg.ParsedNoteType] = {}
    flattened_markup = 0

    for pn in coll.notes:
        nt_meta = coll.note_types.get(pn.note_type_id)
        model = note_type_map.get(pn.note_type_id)
        if model is None or nt_meta is None:
            continue
        raw = [f or "" for f in pn.fields]
        if any(apkg.had_markup(f) for f in raw):
            flattened_markup += 1
        flat = [apkg.flatten_html(f, media_map) for f in raw]

        if nt_meta.is_cloze:
            field_values = {
                "Text": flat[0] if flat else "",
                "Extra": "\n\n".join(x for x in flat[1:] if x),
            }
        else:
            field_values = {
                "Front": flat[0] if flat else "",
                "Back": "\n\n".join(x for x in flat[1:] if x),
            }

        note = Note(user_id=user.id, note_type_id=model.id, field_values=field_values)
        db.add(note)
        await db.flush()
        note_map[pn.anki_id] = note
        note_type_of[pn.anki_id] = nt_meta

        for original, url in media_map.items():
            if original in "".join(raw):
                kind = "audio" if url.lower().endswith((".mp3", ".ogg", ".wav", ".m4a")) else "image"
                db.add(
                    MediaAsset(
                        note_id=note.id,
                        kind=kind,
                        storage_path=url,
                        original_name=original,
                    )
                )

    # ── cards ───────────────────────────────────────────────────────────────
    reviews_by_card: dict[int, list[apkg.ParsedReview]] = {}
    for r in coll.reviews:
        reviews_by_card.setdefault(r.card_id, []).append(r)

    fsrs = FSRSService(desired_retention=user.desired_retention, fuzz=False)
    card_map: dict[int, Card] = {}
    review_logs_mapped = 0

    for pc in coll.cards:
        note = note_map.get(pc.note_id)
        nt_meta = note_type_of.get(pc.note_id)
        if note is None or nt_meta is None:
            continue
        deck = deck_map.get(pc.deck_id, fallback_deck)

        slot = f"c{pc.ord + 1}" if nt_meta.is_cloze else "default" if pc.ord == 0 else f"t{pc.ord}"

        tags = next((n.tags for n in coll.notes if n.anki_id == pc.note_id), [])
        card = Card(
            note_id=note.id,
            deck_id=deck.id,
            template_slot=slot,
            state="new",
            origin="imported",
            lapse_count=pc.lapses,
            suspended=pc.suspended,
            tags=list(tags),
        )
        db.add(card)
        await db.flush()
        card_map[pc.anki_id] = card

        history = sorted(reviews_by_card.get(pc.anki_id, []), key=lambda r: r.reviewed_at)
        if history:
            review_logs_mapped += _replay_history(db, card, history, fsrs)
        elif pc.state != "new":
            # Scheduled in Anki but with no surviving revlog (history is often
            # truncated on export) — keep the due date, leave D/S unknown so the
            # first real review here establishes them.
            card.state = "review" if pc.state == "review" else "learning"
            card.due = pc.due_at or datetime.now(UTC)
            card.last_review = None

    await db.flush()

    # ── warnings & audit row ────────────────────────────────────────────────
    if flattened_markup:
        warnings.append(
            f"{flattened_markup} notes contained HTML formatting, which was flattened to "
            "plain text (images and audio were preserved as links)."
        )
    warnings.extend(sorted(set(unmapped_templates)))
    if not coll.reviews:
        warnings.append(
            "No review history was present in this export, so FSRS could not back-fill "
            "stability/difficulty. Cards keep their due dates and will personalise from "
            "your next reviews."
        )

    record = Import(
        user_id=user.id,
        filename=filename,
        notes_mapped=len(note_map),
        cards_mapped=len(card_map),
        warnings=warnings,
    )
    db.add(record)
    await db.commit()

    # §11: refit parameters at import time rather than waiting for the nightly
    # job — but only when the optional optimizer extra is actually installed.
    optimized = False
    if review_logs_mapped >= 400 and FSRSService.optimizer_available():
        from app.jobs.optimize_fsrs import optimize_user

        try:
            optimized = await optimize_user(db, user)
        except Exception as exc:
            log.warning("import-time FSRS optimize failed: %s", exc)
    elif review_logs_mapped >= 400:
        warnings.append(
            "Review history was imported but the FSRS parameter optimizer is not installed "
            "(rebuild with INSTALL_FSRS_OPTIMIZER=1 to personalise scheduling weights)."
        )
        record.warnings = warnings
        await db.commit()

    return ImportResult(
        id=str(record.id),
        filename=filename,
        notes_mapped=len(note_map),
        cards_mapped=len(card_map),
        review_logs_mapped=review_logs_mapped,
        media_copied=len(media_map),
        decks_created=decks_created,
        warnings=warnings,
        fsrs_optimized=optimized,
    )


def _replay_history(
    db: AsyncSession, card: Card, history: list[apkg.ParsedReview], fsrs: FSRSService
) -> int:
    """Rebuild FSRS state by replaying real reviews (§11 FSRS translation).

    Anki's ease/interval do not map onto D/S, so we don't try: we start the
    card fresh and feed it its own history in order. What comes out is
    stability/difficulty grounded in what the user actually did, plus a full
    review_logs trail that the optimizer can later refit against.
    """
    fsrs_card = FSRSService.to_fsrs_card(
        state="new", stability=None, difficulty=None, step=None, due=None, last_review=None
    )
    state_before = "new"
    written = 0

    for review in history:
        elapsed = None
        if fsrs_card.last_review:
            elapsed = (review.reviewed_at - fsrs_card.last_review).total_seconds() / 86400.0
        fsrs_card, new_state = fsrs.schedule(
            fsrs_card, GRADE_TO_RATING[review.grade], review.reviewed_at
        )
        db.add(
            ReviewLog(
                card_id=card.id,
                reviewed_at=review.reviewed_at,
                latency_ms=review.duration_ms,
                final_grade=review.grade,
                overridden=False,
                state_before=state_before,
                elapsed_days=elapsed,
            )
        )
        written += 1
        state_before = new_state["state"]

    for key, value in FSRSService.from_fsrs_card(fsrs_card).items():
        setattr(card, key, value)
    return written


@router.get("/history")
async def import_history(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> list[dict]:
    rows = (
        await db.scalars(
            select(Import).where(Import.user_id == user.id).order_by(Import.imported_at.desc())
        )
    ).all()
    return [
        {
            "id": str(r.id),
            "filename": r.filename,
            "imported_at": r.imported_at,
            "notes_mapped": r.notes_mapped,
            "cards_mapped": r.cards_mapped,
            "warnings": r.warnings or [],
        }
        for r in rows
    ]
