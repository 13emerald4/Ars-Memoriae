"""Auth: password hashing and session tokens.

Password hashing uses stdlib scrypt so the container needs no bcrypt build step.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time

import jwt

from app.core.config import settings

_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1


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


def create_access_token(user_id: str) -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": str(user_id), "iat": now, "exp": now + settings.access_token_ttl_seconds},
        _signing_key(),
        algorithm="HS256",
    )


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, _signing_key(), algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    return payload.get("sub")


def insecure_defaults() -> list[str]:
    """Surfaced at startup so a self-hosted instance can't silently run on the
    dev fallbacks (§10 puts backup/upgrade responsibility on the operator —
    they should at least be told which secrets are unset)."""
    problems = []
    if settings.secret_key == "dev-insecure-secret-change-me":
        problems.append("SECRET_KEY is the built-in dev default — sessions are forgeable.")
    return problems


def new_answer_hash(answer: str) -> str:
    return hashlib.sha256(answer.strip().lower().encode()).hexdigest()


def random_token() -> str:
    return secrets.token_urlsafe(32)
