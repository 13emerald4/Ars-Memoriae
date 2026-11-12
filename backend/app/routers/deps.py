from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.netutil import is_local_request
from app.core.security import SCOPE_FULL, TokenClaims, decode_token
from app.db import get_db
from app.models import User

bearer = HTTPBearer(auto_error=False)


async def user_for_claims(db: AsyncSession, claims: TokenClaims | None) -> User | None:
    """The account a token speaks for, or None if the token is no longer
    current: unknown user, or issued before the user's last revocation."""
    if claims is None:
        return None
    try:
        user = await db.get(User, uuid.UUID(claims.user_id))
    except ValueError:
        return None
    if user is None or claims.version != user.token_version:
        return None
    return user


async def current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    claims = decode_token(creds.credentials)
    if claims is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired token")
    user = await user_for_claims(db, claims)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired token")
    request.state.token_scope = claims.scope
    return user


async def optional_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if creds is None:
        return None
    claims = decode_token(creds.credentials)
    user = await user_for_claims(db, claims)
    if user is not None and claims is not None:
        request.state.token_scope = claims.scope
    return user


def token_scope(request: Request) -> str:
    return getattr(request.state, "token_scope", SCOPE_FULL)


async def full_session_user(request: Request, user: User = Depends(current_user)) -> User:
    """For account-level actions (password, token minting, revocation): a
    mobile pairing token must not be able to escalate itself."""
    if token_scope(request) != SCOPE_FULL:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "this action needs a full sign-in, not a paired device"
        )
    return user


def code_execution_block_reason(request: Request) -> str | None:
    """Why this caller may not run code on the host, or None if it may.

    Running code is running a program as the backend's OS user. That is only
    offered to a full session on this machine unless the operator opted in.
    """
    if token_scope(request) != SCOPE_FULL:
        return "Paired devices can review cards but cannot run code on the host computer."
    if not settings.allow_remote_code_execution and not is_local_request(request):
        return (
            "Running code is limited to the computer the app is installed on. "
            "To allow it from other devices, set ALLOW_REMOTE_CODE_EXECUTION=1 "
            "in the backend .env and restart."
        )
    return None


async def code_runner_user(request: Request, user: User = Depends(current_user)) -> User:
    """`current_user`, plus the right to execute code on the host. Depends on
    `current_user` so the token's scope is known before it is checked."""
    reason = code_execution_block_reason(request)
    if reason:
        raise HTTPException(status.HTTP_403_FORBIDDEN, reason)
    return user


def parse_uuid(value: str, field: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"invalid {field}") from None
