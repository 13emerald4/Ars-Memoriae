"""Auth: password hashing and session tokens.

Password hashing uses stdlib scrypt so the container needs no bcrypt build step.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass

import jwt

from app.core.config import settings

_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1

# The old built-in default. An instance still configured with it signs tokens
# anyone can forge, so it is called out at startup.
KNOWN_PUBLIC_SECRETS = {"dev-insecure-secret-change-me"}


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_hex, dk_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        dk = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt_hex), n=int(n), r=int(r), p=int(p)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(dk.hex(), dk_hex)


def _signing_key() -> bytes:
    """HS256 wants >= 32 bytes; SECRET_KEY is user-supplied and may be shorter,
    so derive a fixed-width key from it rather than rejecting short secrets."""
    return hashlib.sha256(b"jwt-signing:" + settings.secret_key.encode()).digest()


# What a token may do. "full" is an interactive browser session; "mobile" is
# what the pairing QR hands to the companion app. A mobile token can review
# cards but can never run code on the host or mint further tokens, so a
# photographed QR is not a remote shell.
SCOPE_FULL = "full"
SCOPE_MOBILE = "mobile"
SCOPES = frozenset({SCOPE_FULL, SCOPE_MOBILE})


@dataclass(frozen=True)
class TokenClaims:
    user_id: str
    # Compared against users.token_version; bumping that column revokes every
    # token issued before the bump ("sign out everywhere", password change).
    version: int
    scope: str


def create_access_token(
    user_id: str,
    *,
    version: int = 0,
    scope: str = SCOPE_FULL,
    ttl_seconds: int | None = None,
) -> str:
    now = int(time.time())
    ttl = settings.access_token_ttl_seconds if ttl_seconds is None else ttl_seconds
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
            "exp": now + ttl,
            "ver": int(version),
            "scope": scope,
        },
        _signing_key(),
        algorithm="HS256",
    )


def decode_token(token: str) -> TokenClaims | None:
    """Signature and expiry only. Whether the token is still *current* (its
    version matches the user's) is checked where the user row is loaded."""
    try:
        payload = jwt.decode(token, _signing_key(), algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    scope = payload.get("scope", SCOPE_FULL)
    if scope not in SCOPES:
        return None
    try:
        # Tokens issued before versioning carry no "ver"; they count as 0, so
        # an upgrade doesn't sign anyone out.
        version = int(payload.get("ver", 0))
    except (TypeError, ValueError):
        return None
    return TokenClaims(user_id=str(sub), version=version, scope=scope)


def decode_access_token(token: str) -> str | None:
    claims = decode_token(token)
    return claims.user_id if claims else None


def insecure_defaults() -> list[str]:
    """Surfaced at startup so a self-hosted instance can't silently run on the
    dev fallbacks (§10 puts backup/upgrade responsibility on the operator —
    they should at least be told which secrets are unset)."""
    problems = []
    if settings.secret_key in KNOWN_PUBLIC_SECRETS:
        problems.append("SECRET_KEY is a value published in this repo — sessions are forgeable.")
    return problems


def new_answer_hash(answer: str) -> str:
    return hashlib.sha256(answer.strip().lower().encode()).hexdigest()


def random_token() -> str:
    return secrets.token_urlsafe(32)
