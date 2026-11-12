import pytest

from app.services.hardware_service import HardwareProfile, detect_hardware


def test_detect_hardware_returns_valid_profile():
    detect_hardware.cache_clear()
    profile = detect_hardware()
    assert isinstance(profile, HardwareProfile)
    assert profile.os_name
    assert profile.ram_gb > 0
    assert profile.cpu_cores > 0
    assert profile.cpu_name
    assert profile.hardware_tier in ("budget", "mid-range", "high-end")
    assert profile.recommended_size in ("4b", "7b", "9b")
    assert profile.recommended_model in ("qwen3.5:4b", "qwen2.5-coder:7b", "qwen3.5:9b")
    assert len(profile.models) == 3
    model_ids = [m.id for m in profile.models]
    assert "qwen3.5:9b" in model_ids
    assert "qwen2.5-coder:7b" in model_ids
    assert "qwen3.5:4b" in model_ids

    # Check serialization
    d = profile.to_dict()
    assert d["recommended_model"] == profile.recommended_model
    assert d["ram_gb"] == profile.ram_gb
    assert isinstance(d["models"], list)


async def test_hardware_endpoint_authenticated(auth_client):
    resp = await auth_client.get("/api/llm/hardware")
    assert resp.status_code == 200
    data = resp.json()
    assert "recommended_model" in data
    assert "recommended_size" in data
    assert "ram_gb" in data
    assert "models" in data
    assert len(data["models"]) == 3


async def test_vram_metrics_endpoint(auth_client):
    resp = await auth_client.get("/api/llm/vram")
    assert resp.status_code == 200
    data = resp.json()
    assert "capacity_gb" in data
    assert "available_gb" in data
    assert "used_gb" in data
    assert "model_vram_gb" in data
    assert "model_loaded" in data
    assert data["capacity_gb"] >= 0


def test_detect_hardware_is_cached():
    """Verifies that detect_hardware is wrapped with lru_cache and avoids repeated subprocess calls."""
    detect_hardware.cache_clear()
    info_before = detect_hardware.cache_info()
    assert info_before.hits == 0

    p1 = detect_hardware()
    p2 = detect_hardware()
    assert p1 is p2
    info_after = detect_hardware.cache_info()
    assert info_after.hits >= 1
