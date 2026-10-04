"""BYOK key storage (§4.2) — POST /api/keys."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_api_key, encrypt_api_key, mask_api_key
from app.db import get_db
from app.models import User
from app.routers.deps import current_user
from app.schemas.core import ApiKeyRequest, ApiKeyResponse
from app.services.grading_service import GradingService, GradingUnavailable

router = APIRouter(prefix="/api", tags=["keys"])


@router.post("/keys", response_model=ApiKeyResponse)
async def store_key(
    body: ApiKeyRequest, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> ApiKeyResponse:
    """Store or rotate the user's Google API key.

    The key is verified against the API before being stored, and the reachable
    model list comes back with it: the configured default model ID is only a
    default, and a user whose key cannot reach it needs to see that here rather
    than discovering it mid-review.
    """
    key = body.api_key.strip()
    models: list[str] = []
    warning: str | None = None

    try:
        models = await GradingService(key, user.grading_model).verify_key()
    except GradingUnavailable as exc:
        warning = f"Key stored, but listing models failed: {exc}"

    if models and user.grading_model not in models:
        warning = (
            f"Configured grading model '{user.grading_model}' is not in the list of models "
            "this key can reach. Pick one of available_models in Settings."
        )

    user.google_api_key_encrypted = encrypt_api_key(key)
    await db.commit()
    return ApiKeyResponse(
        stored=True, masked=mask_api_key(key), available_models=models, warning=warning
    )


@router.get("/keys", response_model=ApiKeyResponse)
async def key_status(user: User = Depends(current_user)) -> ApiKeyResponse:
    plaintext = decrypt_api_key(user.google_api_key_encrypted)
    return ApiKeyResponse(stored=bool(plaintext), masked=mask_api_key(plaintext) if plaintext else None)


@router.delete("/keys", response_model=ApiKeyResponse)
async def delete_key(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> ApiKeyResponse:
    user.google_api_key_encrypted = None
    await db.commit()
    return ApiKeyResponse(stored=False)


@router.get("/models")
async def list_models(user: User = Depends(current_user)) -> dict:
    plaintext = decrypt_api_key(user.google_api_key_encrypted)
    try:
        models = await GradingService(plaintext, user.grading_model).verify_key()
        return {"models": models, "active": user.grading_model, "error": None}
    except GradingUnavailable as exc:
        return {"models": [], "active": user.grading_model, "error": str(exc)}


@router.get("/llm/status")
async def llm_status(user: User = Depends(current_user)) -> dict:
    """Checks local Ollama daemon connectivity and Qwen 2.5 Coder availability."""
    service = GradingService(model=user.grading_model)
    try:
        models = await service.verify_engine()
        has_qwen = any("qwen2.5-coder:7b" in m or "qwen2.5-coder" in m for m in models)
        return {
            "connected": True,
            "provider": "ollama",
            "base_url": service.base_url,
            "model": user.grading_model,
            "models_installed": models,
            "model_ready": has_qwen or (user.grading_model in models),
            "error": None,
        }
    except Exception as exc:
        return {
            "connected": False,
            "provider": "ollama",
            "base_url": service.base_url,
            "model": user.grading_model,
            "models_installed": [],
            "model_ready": False,
            "error": str(exc),
        }
