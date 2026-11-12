from __future__ import annotations

import asyncio
from functools import cache

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import login_throttle
from app.core.config import settings
from app.core.security import (
    SCOPE_MOBILE,
    create_access_token,
    hash_password,
    verify_password,
)
from app.db import get_db
from app.models import Deck, NoteType, QueueConfig, User
from app.routers.deps import current_user, full_session_user
from app.schemas.core import (
    ChangePasswordRequest,
    LoginRequest,
    PairingTokenResponse,
    QueueConfigOut,
    QueueConfigUpdate,
    RegisterRequest,
    RegistrationStatus,
    TokenResponse,
    UserOut,
    UserUpdate,
)

router = APIRouter(prefix="/api", tags=["auth"])

# Seeded on registration so a new account can add a card immediately.
STARTER_NOTE_TYPES = [
    ("Basic", "basic", {"fields": ["Front", "Back"]}, "short_answer"),
    ("Cloze", "cloze", {"fields": ["Text", "Extra"]}, "short_answer"),
    ("Conceptual", "basic", {"fields": ["Front", "Back"]}, "conceptual"),
    ("Math / Code", "basic", {"fields": ["Front", "Back"]}, "math_code"),
]


# Nullable settings where an explicit null means "clear it", not "unchanged".
CLEARABLE_USER_FIELDS = frozenset({"target_event_date", "target_event_title"})


def user_out(user: User) -> UserOut:
    from app.services.grading_service import is_antigravity_authorized

    return UserOut(
        id=str(user.id),
        email=user.email,
        desired_retention=user.desired_retention,
        grading_model=user.grading_model,
        queue_time_budget_minutes=user.queue_time_budget_minutes,
        leech_remediation_opt_in=user.leech_remediation_opt_in,
        daily_new_limit=user.daily_new_limit,
        daily_review_limit=user.daily_review_limit,
        backlog_spread_days=user.backlog_spread_days,
        leech_threshold=user.leech_threshold,
        llm_grading_consent=user.llm_grading_consent,
        fsrs_optimized_at=user.fsrs_optimized_at,
        grading_bias=user.grading_bias,
        automaticity_threshold_ms=user.automaticity_threshold_ms,
        target_event_date=user.target_event_date,
        target_event_title=user.target_event_title,
        peak_retention_target=user.peak_retention_target,
        show_pre_leetcode=user.show_pre_leetcode,
        show_code_lab=user.show_code_lab,
        show_thematic_context=user.show_thematic_context,
        tutorial_completed=user.tutorial_completed,
        timezone=user.timezone,
        enable_schema_checkpoints=getattr(user, "enable_schema_checkpoints", True),
        enable_prompt_mutation=getattr(user, "enable_prompt_mutation", False),
        enable_prediction_mode=getattr(user, "enable_prediction_mode", False),
        can_use_antigravity=is_antigravity_authorized(user),
    )


async def registration_open(db: AsyncSession) -> bool:
    """The first account can always sign up; more need ALLOW_REGISTRATION."""
    if settings.allow_registration:
        return True
    return await db.scalar(select(User.id).limit(1)) is None


def _session_token(user: User) -> str:
    return create_access_token(str(user.id), version=user.token_version)


# Serialises sign-ups. "Is this the first account?" and "create it" are two
# statements; without this, two simultaneous requests on a fresh install both
# see an empty table and both get in past a closed registration.
_register_lock = asyncio.Lock()


@router.get("/auth/registration-status", response_model=RegistrationStatus)
async def registration_status(db: AsyncSession = Depends(get_db)) -> RegistrationStatus:
    """Lets the sign-in screen offer "Create an account" only when it would work."""
    return RegistrationStatus(open=await registration_open(db))


@router.post("/auth/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    from app.services.hardware_service import detect_hardware

    email = body.email.lower()
    # Both are CPU / subprocess work; keep them off the event loop.
    password_hash = await asyncio.to_thread(hash_password, body.password)
    hw_profile = await asyncio.to_thread(detect_hardware)

    async with _register_lock:
        if not await registration_open(db):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Sign-up is closed: this instance already has an account. "
                "The operator can set ALLOW_REGISTRATION=1 to allow more.",
            )
        existing = await db.scalar(select(User).where(User.email == email))
        if existing:
            raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")

        user = User(
            email=email,
            password_hash=password_hash,
            grading_model=hw_profile.recommended_model,
        )
        db.add(user)
        await db.flush()

        db.add(QueueConfig(user_id=user.id))
        db.add(Deck(user_id=user.id, name="Default"))
        for name, kind, fields, profile in STARTER_NOTE_TYPES:
            db.add(
                NoteType(
                    user_id=user.id,
                    name=name,
                    template_kind=kind,
                    fields=fields,
                    grading_profile=profile,
                )
            )
        await db.commit()
    return TokenResponse(access_token=_session_token(user))


@cache
def _dummy_hash() -> str:
    """Checked against when the email is unknown, so a miss costs the same
    scrypt time as a wrong password and response timing can't reveal which
    emails have accounts."""
    return hash_password("no account has this password")


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    email = body.email.lower()
    ip = login_throttle.client_ip(request)
    wait = login_throttle.retry_after(ip, email)
    if wait:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"too many failed sign-ins; try again in {wait}s",
            headers={"Retry-After": str(wait)},
        )

    user = await db.scalar(select(User).where(User.email == email))
    stored = user.password_hash if user is not None else _dummy_hash()
    # scrypt takes ~50 ms of CPU; off the event loop so sign-ins don't stall
    # every other request.
    ok = await asyncio.to_thread(verify_password, body.password, stored)
    if user is None or not ok:
        login_throttle.record_failure(ip, email)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    login_throttle.record_success(ip, email)
    return TokenResponse(access_token=_session_token(user))


@router.post("/auth/change-password", response_model=TokenResponse)
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    user: User = Depends(full_session_user),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Sets a new password and revokes every token issued before it, including
    paired devices. The caller gets a fresh token so this session carries on."""
    ip = login_throttle.client_ip(request)
    wait = login_throttle.retry_after(ip, user.email)
    if wait:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"too many failed attempts; try again in {wait}s",
            headers={"Retry-After": str(wait)},
        )
    ok = await asyncio.to_thread(verify_password, body.current_password, user.password_hash)
    if not ok:
        login_throttle.record_failure(ip, user.email)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "current password is incorrect")
    login_throttle.record_success(ip, user.email)
    user.password_hash = await asyncio.to_thread(hash_password, body.new_password)
    user.token_version += 1
    await db.commit()
    await db.refresh(user)
    return TokenResponse(access_token=_session_token(user))


@router.post("/auth/logout-all", response_model=TokenResponse)
async def logout_everywhere(
    user: User = Depends(full_session_user), db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Revokes every token for this account (other browsers, paired phones) and
    returns a new one for the session that asked."""
    user.token_version += 1
    await db.commit()
    await db.refresh(user)
    return TokenResponse(access_token=_session_token(user))


@router.post("/auth/pairing-token", response_model=PairingTokenResponse)
async def pairing_token(user: User = Depends(full_session_user)) -> PairingTokenResponse:
    """A token for the mobile companion's pairing QR.

    Deliberately not the browser's own session token: this one is scoped to
    "mobile" (it can review, but not run code on the host, change the password
    or mint tokens) and is revoked by "sign out everywhere".
    """
    ttl = settings.pairing_token_ttl_seconds
    token = create_access_token(
        str(user.id), version=user.token_version, scope=SCOPE_MOBILE, ttl_seconds=ttl
    )
    return PairingTokenResponse(access_token=token, scope=SCOPE_MOBILE, expires_in=ttl)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(current_user)) -> UserOut:
    return user_out(user)


@router.patch("/me", response_model=UserOut)
async def update_me(
    body: UserUpdate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> UserOut:
    from app.services.grading_service import is_antigravity_authorized, is_antigravity_model

    if (
        body.grading_model is not None
        and is_antigravity_model(body.grading_model)
        and not is_antigravity_authorized(user)
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Antigravity subscription models are only available for authorized owner accounts.",
        )

    for key, value in body.model_dump(exclude_unset=True).items():
        if value is not None or key in CLEARABLE_USER_FIELDS:
            setattr(user, key, value)
    await db.commit()
    await db.refresh(user)
    return user_out(user)


@router.get("/queue-config", response_model=QueueConfigOut)
async def get_queue_config_endpoint(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> QueueConfigOut:
    from app.services.queue_service import get_queue_config

    cfg = await get_queue_config(db, user)
    return QueueConfigOut(**{c: getattr(cfg, c) for c in QueueConfigOut.model_fields})


@router.patch("/queue-config", response_model=QueueConfigOut)
async def update_queue_config(
    body: QueueConfigUpdate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> QueueConfigOut:
    from app.services.queue_service import get_queue_config

    cfg = await get_queue_config(db, user)
    for key, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(cfg, key, value)
    if cfg.review_weight + cfg.new_weight + cfg.ir_weight <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "at least one queue weight must be > 0")
    await db.commit()
    await db.refresh(cfg)
    return QueueConfigOut(**{c: getattr(cfg, c) for c in QueueConfigOut.model_fields})
