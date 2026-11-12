import pytest

from app.schemas.core import UserUpdate
from app.schemas.review import SubmitAnswerRequest, SubmitAnswerResponse
from app.services.grading_service import (
    GradingService,
    VramExhaustedError,
    find_local_fallback_models,
    is_allowed_qwen_coder_model,
    is_memory_or_vram_error,
)


def test_is_allowed_qwen_coder_model():
    # Permitted models across the 3 archetypes:
    # 1. Qwen 3.5 9B (The Heavy Generalist)
    assert is_allowed_qwen_coder_model("qwen3.5:9b") is True
    assert is_allowed_qwen_coder_model("qwen3.5:9b-instruct-q4_K_M") is True
    # 2. Qwen2.5-Coder 7B (The Technical Specialist)
    assert is_allowed_qwen_coder_model("qwen2.5-coder:7b") is True
    assert is_allowed_qwen_coder_model("qwen2.5-coder:7b-instruct-q4_K_M") is True
    # 3. Qwen 3.5 4B / Gemma 4 E4B (The Speed Demon)
    assert is_allowed_qwen_coder_model("qwen3.5:4b") is True
    assert is_allowed_qwen_coder_model("gemma4:e4b") is True
    assert is_allowed_qwen_coder_model("gemma:4b") is True
    # Legacy compatibility sizes
    assert is_allowed_qwen_coder_model("qwen2.5-coder:3b") is True
    assert is_allowed_qwen_coder_model("qwen2.5-coder:1.5b") is True

    # Disallowed models: other sizes, general non-coder, embeddings, rerankers, other families
    assert is_allowed_qwen_coder_model("qwen2.5-coder:14b") is False
    assert is_allowed_qwen_coder_model("qwen2.5-coder:32b") is False
    assert is_allowed_qwen_coder_model("qwen2.5-coder:0.5b") is False
    assert is_allowed_qwen_coder_model("qwen2.5:7b") is False  # general non-coder
    assert is_allowed_qwen_coder_model("llama3.2:3b") is False
    assert is_allowed_qwen_coder_model("qwen3-embedding:8b-q4_K_M") is False
    assert is_allowed_qwen_coder_model("dengcao/Qwen3-Reranker-8B:Q4_K_M") is False
    assert is_allowed_qwen_coder_model("") is False
    assert is_allowed_qwen_coder_model(None) is False


def test_schema_model_validation():
    # UserUpdate schema validation
    u_ok = UserUpdate(grading_model="qwen3.5:4b")
    assert u_ok.grading_model == "qwen3.5:4b"

    with pytest.raises(ValueError):
        UserUpdate(grading_model="llama3.2:3b")

    # SubmitAnswerRequest schema validation
    s_ok = SubmitAnswerRequest(typed_answer="x", latency_ms=100, model="qwen3.5:9b")
    assert s_ok.model == "qwen3.5:9b"

    with pytest.raises(ValueError):
        SubmitAnswerRequest(typed_answer="x", latency_ms=100, model="llama3.2:3b")


def test_is_memory_or_vram_error():
    assert is_memory_or_vram_error("cudaMalloc failed: out of memory")
    assert is_memory_or_vram_error("error loading model: unable to allocate CUDA0 buffer")
    assert is_memory_or_vram_error("memory layout cannot be allocated")
    assert not is_memory_or_vram_error("Connection refused")


@pytest.mark.asyncio
async def test_find_local_fallback_models():
    # Tests that discovery returns models installed in Ollama, strictly restricted to Qwen 2.5 Coder
    fallback, smaller = await find_local_fallback_models("http://127.0.0.1:11434", "qwen2.5-coder:7b")
    assert fallback is not None
    assert "3b" in fallback or "1.5b" in fallback
    assert all("qwen2.5-coder" in m for m in smaller)
    assert not any("gemma" in m for m in smaller)
    assert not any("rerank" in m or "embed" in m for m in smaller)


@pytest.mark.asyncio
async def test_vram_exhausted_error_handling():
    svc = GradingService(model="qwen2.5-coder:7b")

    # Simulate an Ollama OOM error
    async def mock_generate_ollama(prompt, model, schema=None, **kwargs):
        raise RuntimeError("llama runner process has terminated: cudaMalloc failed: out of memory")

    svc._generate_ollama = mock_generate_ollama

    # When allow_smaller_model is False, raises VramExhaustedError with details
    with pytest.raises(VramExhaustedError) as exc_info:
        await svc.grade("Front", "Back", "Answer", allow_smaller_model=False)

    err = exc_info.value
    assert err.failed_model == "qwen2.5-coder:7b"
    assert err.fallback_model is not None


@pytest.mark.asyncio
async def test_auto_fallback_when_allowed():
    svc = GradingService(model="qwen2.5-coder:7b")

    async def mock_generate_ollama(prompt, model, schema=None, **kwargs):
        if model == "qwen2.5-coder:7b":
            raise RuntimeError("cudaMalloc failed: out of memory")
        return '{"score": 85, "confidence": 0.9, "reasoning": "Fallback model graded"}'

    svc._generate_ollama = mock_generate_ollama

    # When allow_smaller_model is True, seamlessly grades with fallback model
    result = await svc.grade_with_escalation(
        "Front", "Back", "Answer", allow_smaller_model=True
    )
    assert result["score"] == 85
    assert result["model_used"] != "qwen2.5-coder:7b"
