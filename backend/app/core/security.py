"""Auth + at-rest encryption of the user's BYOK Google API key (§4.2).

Password hashing uses stdlib scrypt so the container needs no bcrypt build step.
The API key is encrypted with Fernet (AES-128-CBC + HMAC) under
API_KEY_ENCRYPTION_KEY, which is deliberately a *separate* secret from
SECRET_KEY so rotating session signing does not invalidate stored keys.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time

import jwt
from cryptography.fernet import Fernet, InvalidToken

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
    if not settings.api_key_encryption_key:
        problems.append(
            "API_KEY_ENCRYPTION_KEY is unset — stored Google API keys fall back to a key "
            "derived from SECRET_KEY."
        )
    return problems


def _fernet() -> Fernet:
    key = settings.api_key_encryption_key
    if not key:
        # Deterministic dev fallback so a fresh checkout runs; production
        # deployments must set API_KEY_ENCRYPTION_KEY (see .env.example).
        key = base64.urlsafe_b64encode(
            hashlib.sha256(b"dev-fallback:" + settings.secret_key.encode()).digest()
        ).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_api_key(plaintext: str) -> bytes:
    return _fernet().encrypt(plaintext.encode())


def decrypt_api_key(ciphertext: bytes | None) -> str | None:
    if not ciphertext:
        return None
    try:
        return _fernet().decrypt(bytes(ciphertext)).decode()
    except InvalidToken:
        return None


def mask_api_key(plaintext: str) -> str:
    """Shown in Settings so a user can confirm *which* key is stored."""
    if len(plaintext) <= 8:
        return "•" * len(plaintext)
    return f"{plaintext[:4]}{'•' * 8}{plaintext[-4:]}"


def new_answer_hash(answer: str) -> str:
    return hashlib.sha256(answer.strip().lower().encode()).hexdigest()


def random_token() -> str:
    return secrets.token_urlsafe(32)
