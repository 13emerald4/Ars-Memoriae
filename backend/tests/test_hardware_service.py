import pytest
from app.services.hardware_service import detect_hardware, HardwareProfile


def test_detect_hardware_returns_valid_profile():
    profile = detect_hardware()
    assert isinstance(profile, HardwareProfile)
    assert profile.os_name
    assert profile.ram_gb > 0
    assert profile.cpu_cores > 0
    assert profile.cpu_name
    assert profile.hardware_tier in ("budget", "mid-range", "high-end")
    assert profile.recommended_size in ("1.5b", "3b", "7b")
    assert profile.recommended_model in ("qwen2.5-coder:1.5b", "qwen2.5-coder:3b", "qwen2.5-coder:7b")
    assert len(profile.models) == 3

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
