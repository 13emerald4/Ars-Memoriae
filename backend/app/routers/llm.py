"""LLM engine status — local Ollama models and Antigravity subscription CLI (`agy`)."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, status

from app.models import User
from app.routers.deps import current_user
from app.services.grading_service import (
    GradingService,
    GradingUnavailable,
    is_allowed_qwen_coder_model,
    is_antigravity_authorized,
    is_antigravity_model,
    model_provider,
)

router = APIRouter(prefix="/api", tags=["llm"])


@router.get("/models")
async def list_models(user: User = Depends(current_user)) -> dict:
    service = GradingService.for_user(user)
    try:
        engines = await service.verify_all_engines()
    except GradingUnavailable as exc:
        return {
            "models": [],
            "active": service.model,
            "provider": model_provider(service.model),
            "error": str(exc),
        }

    combined = list(
        dict.fromkeys([
            *engines["ollama"]["models"],
            *engines["antigravity"]["models"],
        ])
    )
    active_provider = model_provider(service.model)
    active_err = engines[active_provider]["error"] if not combined else None
    return {
        "models": combined,
        "active": service.model,
        "provider": active_provider,
        "providers": engines,
        "error": active_err,
    }


@router.get("/llm/status")
async def llm_status(user: User = Depends(current_user)) -> dict:
    """Checks both Antigravity subscription CLI (owner only) and local Ollama connectivity, models, and VRAM."""
    from app.services.hardware_service import get_vram_metrics

    service = GradingService.for_user(user)
    engines = await service.verify_all_engines()
    effective_model = service.model
    provider = model_provider(effective_model)
    ollama_info = engines["ollama"]
    agy_info = engines["antigravity"]
    combined = list(dict.fromkeys([*ollama_info["models"], *agy_info["models"]]))

    if provider == "antigravity":
        connected = bool(agy_info["connected"])
        model_ready = connected and is_antigravity_model(effective_model)
        base_url = "Antigravity Subscription (agy CLI)"
        error = agy_info["error"] if not connected else None
        vram_data = None
    else:
        connected = bool(ollama_info["connected"])
        has_qwen = any(is_allowed_qwen_coder_model(m) for m in ollama_info["models"])
        model_ready = has_qwen or (
            is_allowed_qwen_coder_model(effective_model)
            and effective_model in ollama_info["models"]
        )
        base_url = service.base_url
        error = ollama_info["error"] if not connected else None
        # nvidia-smi plus a synchronous HTTP probe: seconds of blocking if run
        # on the event loop, during which no other request is served.
        vram_data = await asyncio.to_thread(get_vram_metrics, effective_model, service.base_url)

    return {
        "connected": connected,
        "provider": provider,
        "base_url": base_url,
        "model": effective_model,
        "models_installed": combined,
        "model_ready": model_ready,
        "error": error,
        "vram": vram_data,
        "providers": engines,
    }


@router.get("/llm/vram")
async def get_vram(model: str | None = None, user: User = Depends(current_user)) -> dict:
    """Returns live VRAM telemetry: capacity, available, and active model VRAM usage."""
    from app.core.config import settings
    from app.services.hardware_service import get_vram_metrics

    if model and is_antigravity_model(model) and not is_antigravity_authorized(user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Antigravity subscription models are only available for authorized owner accounts.",
        )
    target_model = model or GradingService.for_user(user).model
    return await asyncio.to_thread(get_vram_metrics, target_model, settings.ollama_base_url)


@router.get("/llm/hardware")
async def hardware_specs(_user: User = Depends(current_user)) -> dict:
    """Returns detected host hardware specifications and recommended model options."""
    from app.services.hardware_service import detect_hardware

    return (await asyncio.to_thread(detect_hardware)).to_dict()

