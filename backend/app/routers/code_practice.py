"""API router for Coding Practice, LeetCode Problem Studio, and Pre-LeetCode Fundamentals."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timeutil import day_key
from app.db import get_db
from app.models import Card, CodeProblem, CodeSubmission, Deck, Extract, Note, NoteType, Source, StudySession, User
from app.routers.deps import current_user, parse_uuid
from app.schemas.code_practice import (
    AskDeckQuestionRequest,
    AskDeckQuestionResponse,
    CategoryProgression,
    CodeLeechOut,
    CodeProblemOut,
    CodeProblemSummary,
    CodeProgressionStats,
    CodeSubmissionOut,
    DifficultyTierProgression,
    ExplainCodeSelectionRequest,
    ExplainCodeSelectionResponse,
    ExportToDeckRequest,
    ForgeProblemRequest,
    RunCodeRequest,
    RunCodeResponse,
    SocraticCodeRequest,
    SocraticCodeResponse,
    SubmitCodeRequest,
    SubmitCodeResponse,
)
from app.services.code_ai_service import CodeAiService, merge_lexicon_glosses, rank_extracts_for_query
from app.services.code_runner_service import run_code as execute_code
from app.services.fundamentals_catalog import FUNDAMENTALS_CATALOG
from app.services.note_service import sync_cards
from app.services.problems_catalog import PROBLEMS_CATALOG
from app.services.question_format_service import format_question_with_code_blocks
from app.services.rendering import render

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/code", tags=["code_practice"])


async def _load_card_context_for_user(
    db: AsyncSession,
    user: User,
    card_id: str | None,
) -> tuple[Card | None, dict[str, Any]]:
    """Loads owned Card + rendered front/back/tests/weaknesses for LLM context grounding."""
    if not card_id or not str(card_id).strip():
        return None, {}
    try:
        card_uuid = uuid.UUID(str(card_id).strip())
    except ValueError:
        return None, {}

    card_obj = await db.get(Card, card_uuid)
    if card_obj is None:
        return None, {}
    deck_obj = card_obj.deck or await db.get(Deck, card_obj.deck_id)
    if deck_obj is None or deck_obj.user_id != user.id:
        return None, {}

    note = card_obj.note
    fv = note.field_values or {} if note is not None else {}
    template_kind = note.note_type.template_kind if (note is not None and note.note_type is not None) else "basic"
    front, back = render(template_kind, fv, card_obj.template_slot)
    card_tests = str(
        fv.get("starter_tests") or fv.get("ref_tests") or fv.get("test_code") or ""
    ).strip()
    return card_obj, {
        "card_front": front,
        "card_back": back,
        "card_tests": card_tests or None,
        "card_weaknesses": list(card_obj.active_weaknesses or []),
    }


async def _collect_deck_source_ids(
    db: AsyncSession,
    user: User,
    deck_id: str | None,
    doc_id: str | None = None,
) -> list[uuid.UUID]:
    """Walks the deck parent hierarchy to gather attached document source IDs."""
    source_ids: list[uuid.UUID] = []
    if deck_id:
        try:
            curr_deck = await db.get(Deck, parse_uuid(deck_id))
            visited_deck_ids: set[uuid.UUID] = set()
            while curr_deck and curr_deck.user_id == user.id and curr_deck.id not in visited_deck_ids:
                visited_deck_ids.add(curr_deck.id)
                for d in (curr_deck.source_documents or []):
                    if isinstance(d, dict) and d.get("source_id"):
                        try:
                            sid = parse_uuid(d["source_id"])
                            if not doc_id or str(sid) == doc_id or str(d.get("id")) == doc_id:
                                if sid not in source_ids:
                                    source_ids.append(sid)
                        except Exception:
                            pass
                if curr_deck.parent_id:
                    curr_deck = await db.get(Deck, curr_deck.parent_id)
                else:
                    break
        except Exception as exc:
            log.warning("Deck document hierarchy lookup failed: %s", exc)
    if not deck_id and not source_ids:
        user_sources = (
            await db.execute(select(Source.id).where(Source.user_id == user.id).limit(20))
        ).scalars().all()
        source_ids = list(user_sources)
    return source_ids


# Languages the runner can actually execute. Anything else used to come back
# as a fake "Accepted" from /run and a Python compile error from /submit.
RUNNABLE_LANGUAGES = ("python", "typescript", "javascript")


def _runnable_language(language: str) -> str:
    lang = (language or "python").lower().strip()
    if lang not in RUNNABLE_LANGUAGES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Running {language} code isn't supported. Use Python, TypeScript, or JavaScript.",
        )
    return lang


_seed_lock = asyncio.Lock()
_seeded = False


async def ensure_catalog_seeded(db: AsyncSession, force: bool = False) -> None:
    """Seeds or refreshes the default fundamentals and problem catalogs.

    Runs once per process rather than once per request. Previously every
    endpoint re-ran the whole upsert, which meant concurrent requests could
    each observe a newly-added catalog slug as missing and each insert it —
    the frontend fires three requests on page load, so adding N drills to the
    catalog produced N duplicate rows. `slug` cannot simply be made UNIQUE:
    catalog rows have `user_id IS NULL`, and both SQLite and Postgres treat
    NULLs as distinct in a unique index, so the constraint would not bite.
    """
    global _seeded
    if _seeded and not force:
        return

    async with _seed_lock:
        # Re-check: a concurrent caller may have finished while we waited.
        if _seeded and not force:
            return
        await _seed_catalog(db)
        _seeded = True


async def _seed_catalog(db: AsyncSession) -> None:
    stmt = select(CodeProblem).where(CodeProblem.user_id.is_(None))
    rows = (await db.execute(stmt)).scalars().all()

    # Self-heal any duplicates a previous racing build left behind. Keep the
    # oldest row (submissions cascade off problem_id, so the survivor must be
    # the one users have history against) and drop copies nothing points at.
    by_slug: dict[str, list[CodeProblem]] = {}
    for p in rows:
        by_slug.setdefault(p.slug, []).append(p)

    existing_probs: dict[str, CodeProblem] = {}
    for slug, dupes in by_slug.items():
        dupes.sort(key=lambda p: (p.created_at, str(p.id)))
        existing_probs[slug] = dupes[0]
        for extra in dupes[1:]:
            has_history = (
                await db.execute(
                    select(CodeSubmission.id).where(CodeSubmission.problem_id == extra.id).limit(1)
                )
            ).first()
            if has_history is None:
                await db.delete(extra)

    all_catalog_items = list(FUNDAMENTALS_CATALOG) + list(PROBLEMS_CATALOG)
    for item in all_catalog_items:
        slug = item["slug"]
        if slug in existing_probs:
            prob = existing_probs[slug]
            prob.title = item["title"]
            prob.kind = item.get("kind", prob.kind)
            prob.track = item.get("track", prob.track)
            prob.difficulty = item.get("difficulty", prob.difficulty)
            prob.category = item.get("category", prob.category)
            prob.tags = item.get("tags", prob.tags)
            prob.description = item["description"]
            prob.examples = item.get("examples", prob.examples)
            prob.constraints = item.get("constraints", prob.constraints)
            prob.starter_codes = item.get("starter_codes", prob.starter_codes)
            prob.solutions = item.get("solutions", prob.solutions)
            prob.editorial = item.get("editorial", prob.editorial)
            prob.test_cases = item.get("test_cases", prob.test_cases)
            prob.hints = item.get("hints", prob.hints)
        else:
            prob = CodeProblem(
                id=uuid.uuid4(),
                user_id=None,
                kind=item.get("kind", "fundamental"),
                track=item.get("track"),
                title=item["title"],
                slug=item["slug"],
                difficulty=item.get("difficulty", "Easy"),
                category=item.get("category", "General"),
                tags=item.get("tags", []),
                description=item["description"],
                examples=item.get("examples", []),
                constraints=item.get("constraints", []),
                starter_codes=item.get("starter_codes", {}),
                solutions=item.get("solutions", {}),
                editorial=item.get("editorial"),
                test_cases=item.get("test_cases", []),
                hints=item.get("hints", []),
            )
            db.add(prob)

    await db.commit()


async def _get_problem(db: AsyncSession, id_or_slug: str, user: User) -> CodeProblem:
    """Finds a problem by UUID id or string slug."""
    await ensure_catalog_seeded(db)
    try:
        prob_id = uuid.UUID(id_or_slug)
        stmt = select(CodeProblem).where(
            CodeProblem.id == prob_id,
            or_(CodeProblem.user_id.is_(None), CodeProblem.user_id == user.id),
        )
    except ValueError:
        stmt = (
            select(CodeProblem)
            .where(
                CodeProblem.slug == id_or_slug,
                or_(CodeProblem.user_id.is_(None), CodeProblem.user_id == user.id),
            )
            # A slug is not UNIQUE at the DB level, so take the oldest match
            # deterministically. scalar_one_or_none() would raise
            # MultipleResultsFound here and 500 the whole lesson pane.
            .order_by(CodeProblem.created_at, CodeProblem.id)
        )
    prob = (await db.execute(stmt)).scalars().first()
    if prob is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Code problem not found.")
    return prob


@router.get("/problems", response_model=list[CodeProblemSummary])
async def list_problems(
    kind: str | None = Query(None, description="'fundamental' or 'problem'"),
    track: str | None = Query(None),
    category: str | None = Query(None),
    difficulty: str | None = Query(None),
    search: str | None = Query(None),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists code challenges and fundamentals drills with user completion status."""
    await ensure_catalog_seeded(db)

    stmt = select(CodeProblem).where(
        or_(CodeProblem.user_id.is_(None), CodeProblem.user_id == user.id)
    )
    if kind:
        stmt = stmt.where(CodeProblem.kind == kind)
    if track:
        stmt = stmt.where(CodeProblem.track == track)
    if category:
        stmt = stmt.where(CodeProblem.category == category)
    if difficulty:
        stmt = stmt.where(CodeProblem.difficulty == difficulty)
    if search:
        stmt = stmt.where(CodeProblem.title.ilike(f"%{search}%"))

    stmt = stmt.order_by(CodeProblem.created_at.asc())
    problems = (await db.execute(stmt)).scalars().all()

    # Query user submissions for status
    sub_stmt = (
        select(
            CodeSubmission.problem_id,
            CodeSubmission.status,
            func.max(CodeSubmission.created_at),
        )
        .where(CodeSubmission.user_id == user.id)
        .group_by(CodeSubmission.problem_id, CodeSubmission.status)
    )
    sub_rows = (await db.execute(sub_stmt)).all()
    sub_map: dict[uuid.UUID, str] = {}
    for pid, status_val, _ in sub_rows:
        if pid not in sub_map or status_val == "Accepted":
            sub_map[pid] = status_val

    out = []
    for p in problems:
        last_st = sub_map.get(p.id)
        out.append(
            CodeProblemSummary(
                id=str(p.id),
                kind=p.kind,
                track=p.track,
                title=p.title,
                slug=p.slug,
                difficulty=p.difficulty,
                category=p.category,
                tags=p.tags or [],
                has_submission=p.id in sub_map,
                last_status=last_st,
            )
        )
    return out


@router.get("/problems/{id_or_slug}", response_model=CodeProblemOut)
async def get_problem(
    id_or_slug: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves full problem statement, test cases, and editorial."""
    await ensure_catalog_seeded(db)
    p = await _get_problem(db, id_or_slug, user)
    return CodeProblemOut(
        id=str(p.id),
        kind=p.kind,
        track=p.track,
        title=p.title,
        slug=p.slug,
        difficulty=p.difficulty,
        category=p.category,
        tags=p.tags or [],
        description=p.description,
        examples=p.examples or [],
        constraints=p.constraints or [],
        starter_codes=p.starter_codes or {},
        solutions=p.solutions or {},
        editorial=p.editorial,
        test_cases=p.test_cases or [],
        hints=p.hints or [],
        created_at=p.created_at,
    )


@router.post("/problems/{id_or_slug}/run", response_model=RunCodeResponse)
async def run_code(
    id_or_slug: str,
    body: RunCodeRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Executes code against sample or custom testcases in an isolated sandbox."""
    language = _runnable_language(body.language)
    p = await _get_problem(db, id_or_slug, user)
    test_cases_to_run = body.custom_test_cases if body.custom_test_cases else p.test_cases

    res = await execute_code(
        code=body.code,
        test_cases=test_cases_to_run,
        language=language,
        timeout_sec=4.0,
    )
    return RunCodeResponse(
        status=res["status"],
        passed_count=res["passed_count"],
        total_count=res["total_count"],
        runtime_ms=res["runtime_ms"],
        error=res.get("error"),
        results=res["results"],
    )


@router.post("/problems/{id_or_slug}/submit", response_model=SubmitCodeResponse)
async def submit_code(
    id_or_slug: str,
    body: SubmitCodeRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submits code against all testcases and records submission log."""
    language = _runnable_language(body.language)
    p = await _get_problem(db, id_or_slug, user)

    res = await execute_code(
        code=body.code,
        test_cases=p.test_cases,
        language=language,
        timeout_sec=5.0,
    )

    submission = CodeSubmission(
        id=uuid.uuid4(),
        user_id=user.id,
        problem_id=p.id,
        language=language,
        code=body.code,
        status=res["status"],
        passed_tests=res["passed_count"],
        total_tests=res["total_count"],
        runtime_ms=res["runtime_ms"],
        memory_kb=1024.0,
        ai_feedback=None,
    )
    db.add(submission)
    await db.commit()

    return SubmitCodeResponse(
        submission_id=str(submission.id),
        status=res["status"],
        passed_count=res["passed_count"],
        total_count=res["total_count"],
        runtime_ms=res["runtime_ms"],
        results=res["results"],
    )


@router.post("/problems/{id_or_slug}/socratic", response_model=SocraticCodeResponse)
async def socratic_hint(
    id_or_slug: str,
    body: SocraticCodeRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generates Socratic AI guidance without giving away the direct answer."""
    from app.services.grading_service import GradingUnavailable

    p = await _get_problem(db, id_or_slug, user)
    ai_svc = CodeAiService.for_user(user, body.model)
    try:
        hint_text = await ai_svc.socratic_hint(
            title=p.title,
            description=p.description,
            language=body.language,
            code=body.code,
            hint_type=body.hint_type,
        )
    except GradingUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return SocraticCodeResponse(hint=hint_text)


@router.post("/explain-selection", response_model=ExplainCodeSelectionResponse)
async def explain_code_selection(
    body: ExplainCodeSelectionRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> ExplainCodeSelectionResponse:
    """Finds information within attached deck docs for selected code using local LLM."""
    if not body.selected_code or not body.selected_code.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="selected_code cannot be empty",
        )
    ai_svc = CodeAiService.for_user(user, body.model)
    try:
        _, card_ctx = await _load_card_context_for_user(db, user, body.card_id)
        source_ids = await _collect_deck_source_ids(db, user, body.deck_id, body.doc_id)

        if source_ids:
            rows = (
                await db.execute(
                    select(Extract, Source)
                    .join(Source, Extract.source_id == Source.id)
                    .where(Extract.source_id.in_(source_ids))
                )
            ).all()
            if rows:
                top_excerpts = rank_extracts_for_query(
                    query=body.selected_code,
                    extracts_with_sources=rows,
                    top_k=5,
                )
                res = await ai_svc.query_deck_docs(
                    query=body.selected_code,
                    doc_excerpts=top_excerpts,
                    full_code=body.full_code,
                    language=body.language,
                    model=ai_svc.grading_service.model,
                    context=body.context,
                    user_code=body.user_code,
                    user_test_code=body.user_test_code,
                    execution_summary=body.execution_summary,
                    revealed=body.revealed,
                    **card_ctx,
                )
                sections = []
                citation = res.get("doc_citation") or "Deck Documentation"
                sections.append(f"**→ Cited Document.** {citation}")

                verbatim = res.get("verbatim_passage")
                if verbatim:
                    sections.append(f"**→ Verbatim Specification.**\n> {verbatim}")

                meaning = res.get("explanation") or res.get("found_info")
                if meaning and meaning != verbatim:
                    sections.append(f"**→ Meaning & Application.** {meaning}")

                takeaway = res.get("key_takeaway")
                if takeaway:
                    sections.append(f"**→ Key Takeaway.** {takeaway}")

                formatted_explanation = "\n\n".join(sections).strip()

                return ExplainCodeSelectionResponse(
                    explanation=formatted_explanation,
                    occams_razor=res.get("explanation"),
                    socratic_insight=res.get("key_takeaway"),
                    doc_citation=res.get("doc_citation"),
                    verbatim_passage=res.get("verbatim_passage"),
                    doc_matches=res.get("citations", []),
                    model_used=res.get("model_used", ai_svc.grading_service.model),
                    available_models=res.get("available_models", []),
                )

        formatted_explanation = (
            "**→ Cited Document.** Deck Documentation\n\n"
            "**→ Meaning & Application.** No documentation attached to this deck or its parent decks.\n\n"
            "**→ Key Takeaway.** Upload documentation (.pdf, .md, .txt, code files) using the '📄 Deck Docs' button in the deck view to search specifications and ground code."
        )
        return ExplainCodeSelectionResponse(
            explanation=formatted_explanation,
            occams_razor=None,
            socratic_insight=None,
            doc_citation=None,
            verbatim_passage=None,
            doc_matches=[],
            model_used=ai_svc.grading_service.model,
            available_models=[],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Documentation search failed: {exc}",
        ) from exc


@router.post("/ask-docs", response_model=AskDeckQuestionResponse)
async def ask_deck_docs(
    body: AskDeckQuestionRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> AskDeckQuestionResponse:
    """Answers a user's follow-up question grounded in card context, student work, code, and attached deck documentation."""
    if not body.question or not body.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="question cannot be empty",
        )
    ai_svc = CodeAiService.for_user(user, body.model)
    try:
        card_obj, card_ctx = await _load_card_context_for_user(db, user, body.card_id)
        source_ids = await _collect_deck_source_ids(db, user, body.deck_id, body.doc_id)

        top_excerpts = []
        if source_ids:
            rows = (
                await db.execute(
                    select(Extract, Source)
                    .join(Source, Extract.source_id == Source.id)
                    .where(Extract.source_id.in_(source_ids))
                )
            ).all()
            if rows:
                search_query = f"{body.question} {body.selected_code or ''}".strip()
                top_excerpts = rank_extracts_for_query(
                    query=search_query,
                    extracts_with_sources=rows,
                    top_k=5,
                )

        res = await ai_svc.ask_deck_question(
            question=body.question,
            doc_excerpts=top_excerpts,
            selected_code=body.selected_code,
            full_code=body.full_code,
            language=body.language,
            history=body.history,
            model=ai_svc.grading_service.model,
            context=body.context,
            user_code=body.user_code,
            user_test_code=body.user_test_code,
            execution_summary=body.execution_summary,
            revealed=body.revealed,
            **card_ctx,
        )

        extracted_glosses = res.get("extracted_glosses", []) or []
        updated_card_glosses: list[dict] | None = None

        if card_obj is not None and extracted_glosses:
            try:
                merged = merge_lexicon_glosses(card_obj.lexicon_glosses, extracted_glosses)
                card_obj.lexicon_glosses = list(merged)
                await db.commit()
                await db.refresh(card_obj)
                updated_card_glosses = list(card_obj.lexicon_glosses or [])
            except Exception as card_err:
                log.warning("Failed to auto-populate card lexicon_glosses for card %s: %s", body.card_id, card_err)

        return AskDeckQuestionResponse(
            answer=res.get("answer", ""),
            doc_citation=res.get("doc_citation"),
            citations=res.get("citations", []),
            model_used=res.get("model_used", ai_svc.grading_service.model),
            available_models=res.get("available_models", []),
            extracted_glosses=extracted_glosses,
            updated_card_glosses=updated_card_glosses,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Documentation question failed: {exc}",
        ) from exc



@router.post("/problems/forge", response_model=CodeProblemOut)
async def forge_problem(
    body: ForgeProblemRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Uses Qwen 2.5 Coder to generate a custom code challenge from a topic."""
    ai_svc = CodeAiService.for_user(user)
    try:
        generated = await ai_svc.forge_problem(
            topic=body.topic,
            difficulty=body.difficulty,
            target_language=body.target_language,
        )
    except Exception as e:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"Failed to forge problem using Qwen 2.5 Coder: {e}",
        ) from e

    slug = generated.get("slug") or f"custom-{uuid.uuid4().hex[:8]}"
    starter_map = generated.get("starter_codes", {}) or {}
    primary_starter = (
        starter_map.get(body.target_language)
        or next(iter(starter_map.values()), "")
        if isinstance(starter_map, dict)
        else ""
    )
    formatted_description = format_question_with_code_blocks(
        generated.get("description", ""),
        starter_code=primary_starter,
        language=body.target_language,
    )
    prob = CodeProblem(
        id=uuid.uuid4(),
        user_id=user.id,
        kind="problem",
        track=None,
        title=generated.get("title", f"Challenge: {body.topic}"),
        slug=slug,
        difficulty=generated.get("difficulty", body.difficulty),
        category=generated.get("category", "AI Generated"),
        tags=generated.get("tags", [body.topic]),
        description=formatted_description,
        examples=generated.get("examples", []),
        constraints=generated.get("constraints", []),
        starter_codes=starter_map,
        solutions=generated.get("solutions", {}),
        editorial=generated.get("editorial"),
        test_cases=generated.get("test_cases", []),
        hints=generated.get("hints", []),
    )
    db.add(prob)
    await db.commit()
    await db.refresh(prob)

    return CodeProblemOut(
        id=str(prob.id),
        kind=prob.kind,
        track=prob.track,
        title=prob.title,
        slug=prob.slug,
        difficulty=prob.difficulty,
        category=prob.category,
        tags=prob.tags,
        description=prob.description,
        examples=prob.examples,
        constraints=prob.constraints,
        starter_codes=prob.starter_codes,
        solutions=prob.solutions,
        editorial=prob.editorial,
        test_cases=prob.test_cases,
        hints=prob.hints,
        created_at=prob.created_at,
    )


@router.post("/problems/{id_or_slug}/export-card")
async def export_problem_to_card(
    id_or_slug: str,
    body: ExportToDeckRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Exports a coding problem to a deck as a spaced repetition flashcard."""
    p = await _get_problem(db, id_or_slug, user)
    deck_id = parse_uuid(body.deck_id, "deck_id")
    deck = await db.get(Deck, deck_id)
    if not deck or deck.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deck not found.")

    # Find or default to Math/Code note type
    nt_stmt = select(NoteType).where(
        NoteType.user_id == user.id,
        NoteType.grading_profile == "math_code",
    )
    nt = (await db.execute(nt_stmt)).scalar_one_or_none()
    if not nt:
        nt_stmt_any = select(NoteType).where(NoteType.user_id == user.id)
        nt = (await db.execute(nt_stmt_any)).scalar_one_or_none()

    if not nt:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No valid note type found.")

    lang = (
        "typescript"
        if "typescript" in (p.starter_codes or {})
        else ("python" if "python" in (p.starter_codes or {}) else next(iter(p.starter_codes or {}), "python"))
    )
    sol = (p.solutions or {}).get(lang) or next(iter((p.solutions or {}).values()), "")
    starter = (p.starter_codes or {}).get(lang) or ""
    starter_tests = (
        (p.starter_codes or {}).get("starter_tests")
        or (p.starter_codes or {}).get(f"{lang}_tests")
        or (p.starter_codes or {}).get("tests")
    )

    raw_front = f"### {p.title}\n\n{p.description}\n\n**Constraints:**\n" + "\n".join(
        f"- {c}" for c in p.constraints
    )
    fv = {
        "Front": format_question_with_code_blocks(raw_front, starter_code=starter, language=lang),
        "Back": sol,
        "title": p.title,
        "starter_code": starter,
        "language": lang,
        "test_cases": p.test_cases or [],
        "difficulty": p.difficulty,
        "category": p.category,
    }
    if starter_tests:
        fv["starter_tests"] = starter_tests

    note = Note(
        id=uuid.uuid4(),
        user_id=user.id,
        note_type_id=nt.id,
        field_values=fv,
    )
    db.add(note)
    await db.flush()
    await sync_cards(db, note, nt, deck.id)
    await db.commit()

    card_stmt = select(Card).where(Card.note_id == note.id)
    card = (await db.execute(card_stmt)).scalars().first()

    return {
        "note_id": str(note.id),
        "card_id": str(card.id) if card else None,
        "message": f"Exported '{p.title}' to deck '{deck.name}'.",
    }


@router.get("/submissions", response_model=list[CodeSubmissionOut])
async def list_submissions(
    problem_id: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves user's recent code submission records."""
    stmt = select(CodeSubmission).where(CodeSubmission.user_id == user.id)
    if problem_id:
        pid = parse_uuid(problem_id, "problem_id")
        stmt = stmt.where(CodeSubmission.problem_id == pid)
    stmt = stmt.order_by(CodeSubmission.created_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        CodeSubmissionOut(
            id=str(r.id),
            problem_id=str(r.problem_id),
            language=r.language,
            code=r.code,
            status=r.status,
            passed_tests=r.passed_tests,
            total_tests=r.total_tests,
            runtime_ms=r.runtime_ms,
            created_at=r.created_at,
        )
        for r in rows
    ]


def _interval_bucket(days: float) -> str:
    if days < 1:
        return "<1d"
    if days < 3:
        return "1-3d"
    if days < 7:
        return "3-7d"
    if days < 14:
        return "7-14d"
    if days < 30:
        return "14-30d"
    return "30d+"


@router.get("/stats", response_model=CodeProgressionStats)
async def code_stats(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> CodeProgressionStats:
    """Computes Blind 75 learning and performance progression statistics.

    Mirrors the cognitive performance metrics used for memorization cards:
    heatmaps, FSRS memory stability/difficulty, interval retention curves,
    velocity (mastered/hr), and leech detection for recurring failure patterns.
    """
    await ensure_catalog_seeded(db)

    # 1. Fetch all problems of kind="problem"
    p_stmt = select(CodeProblem).where(
        CodeProblem.kind == "problem",
        or_(CodeProblem.user_id.is_(None), CodeProblem.user_id == user.id),
    )
    problems = (await db.execute(p_stmt)).scalars().all()
    seen_slugs = set()
    unique_problems = []
    for p in problems:
        if p.slug not in seen_slugs:
            seen_slugs.add(p.slug)
            unique_problems.append(p)

    # 2. Fetch all user submissions
    sub_stmt = (
        select(CodeSubmission)
        .where(CodeSubmission.user_id == user.id)
        .order_by(CodeSubmission.created_at.asc())
    )
    subs = (await db.execute(sub_stmt)).scalars().all()

    subs_by_pid: dict[uuid.UUID, list[CodeSubmission]] = defaultdict(list)
    heatmap: dict[str, int] = defaultdict(int)
    for s in subs:
        subs_by_pid[s.problem_id].append(s)
        heatmap[day_key(s.created_at, user.timezone)] += 1

    prob_by_id = {p.id: p for p in unique_problems}
    solved_pids: set[uuid.UUID] = set()
    attempted_pids: set[uuid.UUID] = set()
    first_try_pids: set[uuid.UUID] = set()
    lapse_counts: dict[uuid.UUID, int] = defaultdict(int)
    last_error_map: dict[uuid.UUID, str] = {}

    bucket_hit: dict[str, int] = defaultdict(int)
    bucket_total: dict[str, int] = defaultdict(int)

    for pid, p_subs in subs_by_pid.items():
        if not p_subs:
            continue
        attempted_pids.add(pid)
        if any(s.status == "Accepted" for s in p_subs):
            solved_pids.add(pid)
        if p_subs[0].status == "Accepted":
            first_try_pids.add(pid)

        failures = [s for s in p_subs if s.status != "Accepted"]
        lapse_counts[pid] = len(failures)
        if failures:
            last_error_map[pid] = failures[-1].status

        # Interval retention calculation on repeat submissions
        for i in range(1, len(p_subs)):
            dt_days = (p_subs[i].created_at - p_subs[i - 1].created_at).total_seconds() / 86400.0
            bucket = _interval_bucket(dt_days)
            bucket_total[bucket] += 1
            if p_subs[i].status == "Accepted":
                bucket_hit[bucket] += 1

    retention = {
        bucket: round(bucket_hit[bucket] / bucket_total[bucket], 4)
        for bucket in bucket_total
        if bucket_total[bucket] >= 1
    }

    # Leech detection (failing repeated submissions)
    leeches = []
    for pid, count in lapse_counts.items():
        if count >= 2 and pid in prob_by_id:
            prob = prob_by_id[pid]
            leeches.append(
                CodeLeechOut(
                    problem_id=str(pid),
                    slug=prob.slug,
                    title=prob.title,
                    difficulty=prob.difficulty,
                    category=prob.category,
                    lapse_count=count,
                    last_error=last_error_map.get(pid),
                    suggestion_kind="Socratic Guidance",
                    suggestion_rationale=f"Repeated difficulties with {prob.title} ({count} failed runs). Inspect editorial and pattern invariants.",
                )
            )
    leeches.sort(key=lambda leech: leech.lapse_count, reverse=True)

    STANDARD_CATEGORIES = [
        "Arrays & Hashing", "Two Pointers", "Sliding Window", "Stack",
        "Binary Search", "Linked List", "Trees", "Tries",
        "Heap / Priority Queue", "Backtracking", "Graphs", "Advanced Graphs",
        "1-D Dynamic Programming", "2-D Dynamic Programming", "Greedy",
        "Intervals", "Math & Geometry", "Bit Manipulation"
    ]
    all_cats = list(STANDARD_CATEGORIES)
    for p in unique_problems:
        if p.category not in all_cats:
            all_cats.append(p.category)

    category_prog = []
    for cat in all_cats:
        cat_probs = [p for p in unique_problems if p.category == cat]
        if not cat_probs:
            continue
        c_total = len(cat_probs)
        c_solved = sum(1 for p in cat_probs if p.id in solved_pids)
        c_attempted = sum(1 for p in cat_probs if p.id in attempted_pids)
        pct = round((c_solved / c_total) * 100, 1) if c_total > 0 else 0.0
        category_prog.append(
            CategoryProgression(
                category=cat,
                total=c_total,
                solved=c_solved,
                attempted=c_attempted,
                percentage=pct,
            )
        )

    difficulty_prog = {}
    for diff in ["Easy", "Medium", "Hard"]:
        diff_probs = [p for p in unique_problems if p.difficulty.lower() == diff.lower()]
        d_total = len(diff_probs)
        d_solved = sum(1 for p in diff_probs if p.id in solved_pids)
        d_attempted = sum(1 for p in diff_probs if p.id in attempted_pids)
        pct = round((d_solved / d_total) * 100, 1) if d_total > 0 else 0.0
        difficulty_prog[diff.lower()] = DifficultyTierProgression(
            total=d_total,
            solved=d_solved,
            attempted=d_attempted,
            percentage=pct,
        )

    # Active study session velocity
    now = datetime.now(UTC)
    since = now - timedelta(days=365)
    active_seconds = await db.scalar(
        select(func.sum(StudySession.active_seconds)).where(
            StudySession.user_id == user.id,
            StudySession.ended_at.isnot(None),
            StudySession.started_at >= since,
        )
    )
    active_hours = (active_seconds or 0) / 3600.0
    mastered_total = float(len(solved_pids))
    velocity_rate = round(mastered_total / active_hours, 2) if active_hours > 0.05 else mastered_total

    # FSRS stability and difficulty across the user's cards. Averaged in SQL
    # (AVG skips NULLs) rather than loading the whole collection.
    avg_stab_raw, avg_diff_raw = (
        await db.execute(
            select(func.avg(Card.stability), func.avg(Card.difficulty))
            .join(Deck, Deck.id == Card.deck_id)
            .where(Deck.user_id == user.id)
        )
    ).one()
    avg_stab = round(avg_stab_raw, 1) if avg_stab_raw is not None else 21.0
    avg_diff = round(avg_diff_raw, 2) if avg_diff_raw is not None else 0.45

    # Only cards due inside the 30-day window are fetched.
    forecast: dict[str, int] = defaultdict(int)
    horizon = now + timedelta(days=30)
    due_dates = (
        await db.scalars(
            select(Card.due)
            .join(Deck, Deck.id == Card.deck_id)
            .where(
                Deck.user_id == user.id,
                Card.state != "new",
                Card.due.isnot(None),
                Card.due <= horizon,
            )
        )
    ).all()
    for due in due_dates:
        forecast[day_key(max(due if due.tzinfo else due.replace(tzinfo=UTC), now), user.timezone)] += 1

    totals = {
        "cards": float(len(unique_problems)),
        "in_review": float(len(attempted_pids)),
        "solved": mastered_total,
        "attempted": float(len(attempted_pids)),
        "reviews_logged": float(len(subs)),
        "avg_stability_days": avg_stab,
        "avg_difficulty": avg_diff,
        "first_try_solves": float(len(first_try_pids)),
    }

    velocity = {
        "rate": float(velocity_rate),
        "mastered_in_sessions": mastered_total,
        "mastered_total": mastered_total,
        "active_hours": round(active_hours, 2),
    }

    recent_activity = [
        CodeSubmissionOut(
            id=str(s.id),
            problem_id=str(s.problem_id),
            language=s.language,
            code=s.code,
            status=s.status,
            passed_tests=s.passed_tests,
            total_tests=s.total_tests,
            runtime_ms=s.runtime_ms,
            created_at=s.created_at,
        )
        for s in subs[-10:][::-1]
    ]

    return CodeProgressionStats(
        totals=totals,
        velocity=velocity,
        retention=retention,
        heatmap=heatmap,
        forecast=forecast,
        leeches=leeches,
        categories=category_prog,
        difficulty=difficulty_prog,
        recent_activity=recent_activity,
    )

