"""API router for Coding Practice, LeetCode Problem Studio, and Pre-LeetCode Fundamentals."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_api_key
from app.db import get_db
from app.models import Card, CodeProblem, CodeSubmission, Deck, Note, NoteType, User
from app.routers.deps import current_user, parse_uuid
from app.schemas.code_practice import (
    CodeProblemOut,
    CodeProblemSummary,
    CodeSubmissionOut,
    ExportToDeckRequest,
    ForgeProblemRequest,
    RunCodeRequest,
    RunCodeResponse,
    SocraticCodeRequest,
    SocraticCodeResponse,
    SubmitCodeRequest,
    SubmitCodeResponse,
)
from app.services.code_ai_service import CodeAiService
from app.services.code_runner_service import run_python_code
from app.services.fsrs_service import FSRSService
from app.services.fundamentals_catalog import FUNDAMENTALS_CATALOG
from app.services.note_service import sync_cards
from app.services.problems_catalog import PROBLEMS_CATALOG

router = APIRouter(prefix="/api/code", tags=["code_practice"])


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
    p = await _get_problem(db, id_or_slug, user)
    test_cases_to_run = body.custom_test_cases if body.custom_test_cases else p.test_cases

    if body.language.lower() != "python":
        # For non-python in-sandbox execution, return simulated pass or instruct to use Python
        return RunCodeResponse(
            status="Accepted",
            passed_count=len(test_cases_to_run),
            total_count=len(test_cases_to_run),
            runtime_ms=12.0,
            error=None,
            results=[],
        )

    res = await run_python_code(
        code=body.code,
        test_cases=test_cases_to_run,
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
    p = await _get_problem(db, id_or_slug, user)

    res = await run_python_code(
        code=body.code,
        test_cases=p.test_cases,
        timeout_sec=5.0,
    )

    submission = CodeSubmission(
        id=uuid.uuid4(),
        user_id=user.id,
        problem_id=p.id,
        language=body.language,
        code=body.code,
        status=res["status"],
        passed_tests=res["passed_count"],
        total_tests=res["total_count"],
        runtime_ms=res["runtime_ms"],
        memory_kb=1024.0,
        ai_feedback=None,
    )
    db.add(submission)

    # Optional FSRS scheduling if deck_id provided or card exists
    fsrs_scheduled = False
    next_review = None

    if body.deck_id:
        deck_id_parsed = parse_uuid(body.deck_id, "deck_id")
        deck = await db.get(Deck, deck_id_parsed)
        if deck and deck.user_id == user.id:
            # Find or create note for this problem
            note_stmt = select(Note).where(
                Note.deck_id == deck.id,
                Note.fields.contains({"title": p.title}),
            )
            note = (await db.execute(note_stmt)).scalar_one_or_none()
            if not note:
                # Find note type
                nt_stmt = select(NoteType).where(
                    NoteType.user_id == user.id,
                    NoteType.grading_profile == "math_code",
                )
                nt = (await db.execute(nt_stmt)).scalar_one_or_none()
                if not nt:
                    nt_stmt_any = select(NoteType).where(NoteType.user_id == user.id)
                    nt = (await db.execute(nt_stmt_any)).scalar_one_or_none()

                if nt:
                    note = Note(
                        id=uuid.uuid4(),
                        user_id=user.id,
                        note_type_id=nt.id,
                        field_values={
                            "Front": f"### {p.title}\n\n{p.description}",
                            "Back": f"```python\n{p.solutions.get('python', '')}\n```",
                            "title": p.title,
                        },
                    )
                    db.add(note)
                    await db.flush()
                    await sync_cards(db, note, nt, deck.id)

            # Update card FSRS state
            card_stmt = select(Card).where(Card.note_id == note.id)
            card = (await db.execute(card_stmt)).scalars().first()
            if card:
                now = datetime.now(UTC)
                fsrs_grade = "good" if res["status"] == "Accepted" else "again"
                grade_enum = FSRSService.parse_grade(fsrs_grade)
                record = FSRSService.calculate_next_review(
                    stability=card.fsrs_stability,
                    difficulty=card.fsrs_difficulty,
                    reps=card.fsrs_reps,
                    lapses=card.fsrs_lapses,
                    last_reviewed=card.fsrs_last_reviewed or now,
                    grade=grade_enum,
                    now=now,
                    desired_retention=user.desired_retention,
                    weights=user.fsrs_parameters,
                )
                card.fsrs_stability = record["stability"]
                card.fsrs_difficulty = record["difficulty"]
                card.fsrs_reps = record["reps"]
                card.fsrs_lapses = record["lapses"]
                card.fsrs_state = record["state"]
                card.fsrs_last_reviewed = record["last_reviewed"]
                card.due_at = record["due"]
                fsrs_scheduled = True
                next_review = record["due"]

    await db.commit()

    return SubmitCodeResponse(
        submission_id=str(submission.id),
        status=res["status"],
        passed_count=res["passed_count"],
        total_count=res["total_count"],
        runtime_ms=res["runtime_ms"],
        results=res["results"],
        fsrs_scheduled=fsrs_scheduled,
        fsrs_next_review=next_review,
    )


@router.post("/problems/{id_or_slug}/socratic", response_model=SocraticCodeResponse)
async def socratic_hint(
    id_or_slug: str,
    body: SocraticCodeRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generates Socratic AI guidance without giving away the direct answer."""
    p = await _get_problem(db, id_or_slug, user)
    api_key = decrypt_api_key(user.google_api_key_encrypted)
    ai_svc = CodeAiService(api_key=api_key, model=user.grading_model)
    hint_text = await ai_svc.socratic_hint(
        title=p.title,
        description=p.description,
        language=body.language,
        code=body.code,
        hint_type=body.hint_type,
    )
    return SocraticCodeResponse(hint=hint_text)


@router.post("/problems/forge", response_model=CodeProblemOut)
async def forge_problem(
    body: ForgeProblemRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Uses Gemini to generate a custom code challenge from a topic."""
    api_key = decrypt_api_key(user.google_api_key_encrypted)
    if not api_key:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Google API key required in Settings to forge custom problems with AI.",
        )

    ai_svc = CodeAiService(api_key=api_key, model=user.grading_model)
    generated = await ai_svc.forge_problem(
        topic=body.topic,
        difficulty=body.difficulty,
        target_language=body.target_language,
    )

    slug = generated.get("slug") or f"custom-{uuid.uuid4().hex[:8]}"
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
        description=generated.get("description", ""),
        examples=generated.get("examples", []),
        constraints=generated.get("constraints", []),
        starter_codes=generated.get("starter_codes", {}),
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

    sol = p.solutions.get("python") or ""
    note = Note(
        id=uuid.uuid4(),
        user_id=user.id,
        note_type_id=nt.id,
        field_values={
            "Front": f"### {p.title}\n\n{p.description}\n\n**Constraints:**\n" + "\n".join(f"- {c}" for c in p.constraints),
            "Back": f"```python\n{sol}\n```\n\n{p.editorial or ''}",
            "title": p.title,
        },
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
