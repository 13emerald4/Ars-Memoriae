"""Local LLM engine status — which Ollama models are installed and ready."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.models import User
from app.routers.deps import current_user
from app.services.grading_service import GradingService, GradingUnavailable

router = APIRouter(prefix="/api", tags=["llm"])


@router.get("/models")
async def list_models(user: User = Depends(current_user)) -> dict:
    try:
        models = await GradingService(model=user.grading_model).verify_engine()
        return {"models": models, "active": user.grading_model, "error": None}
    except GradingUnavailable as exc:
        return {"models": [], "active": user.grading_model, "error": str(exc)}


@router.get("/llm/status")
async def llm_status(user: User = Depends(current_user)) -> dict:
    """Checks local Ollama daemon connectivity and Qwen 2.5 Coder availability."""
    from app.services.grading_service import is_allowed_qwen_coder_model

    service = GradingService(model=user.grading_model)
    try:
        models = await service.verify_engine()
        has_qwen = any(is_allowed_qwen_coder_model(m) for m in models)
        return {
            "connected": True,
            "provider": "ollama",
            "base_url": service.base_url,
            "model": service.model,
            "models_installed": models,
            "model_ready": has_qwen or (is_allowed_qwen_coder_model(user.grading_model) and user.grading_model in models),
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


@router.get("/llm/hardware")
async def hardware_specs(_user: User = Depends(current_user)) -> dict:
    """Returns detected host hardware specifications and recommended Qwen 2.5 Coder model size."""
    from app.services.hardware_service import detect_hardware

    return detect_hardware().to_dict()

