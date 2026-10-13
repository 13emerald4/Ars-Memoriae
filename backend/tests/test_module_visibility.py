import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_module_visibility_defaults_and_toggle(auth_client: AsyncClient):
    # 1. Default registration: show_pre_leetcode and show_code_lab must both be False
    me_resp = await auth_client.get("/api/me")
    assert me_resp.status_code == 200, me_resp.text
    data = me_resp.json()
    assert data["show_pre_leetcode"] is False
    assert data["show_code_lab"] is False

    # 2. Toggle show_pre_leetcode on
    patch_resp = await auth_client.patch(
        "/api/me",
        json={"show_pre_leetcode": True},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    patched = patch_resp.json()
    assert patched["show_pre_leetcode"] is True
    assert patched["show_code_lab"] is False

    # Verify persistence via fresh GET /api/me
    verify_resp = await auth_client.get("/api/me")
    assert verify_resp.status_code == 200
    assert verify_resp.json()["show_pre_leetcode"] is True
    assert verify_resp.json()["show_code_lab"] is False

    # 3. Toggle show_code_lab on
    patch_resp2 = await auth_client.patch(
        "/api/me",
        json={"show_code_lab": True},
    )
    assert patch_resp2.status_code == 200, patch_resp2.text
    patched2 = patch_resp2.json()
    assert patched2["show_pre_leetcode"] is True
    assert patched2["show_code_lab"] is True

    # 4. Toggle show_pre_leetcode off independently
    patch_resp3 = await auth_client.patch(
        "/api/me",
        json={"show_pre_leetcode": False},
    )
    assert patch_resp3.status_code == 200, patch_resp3.text
    patched3 = patch_resp3.json()
    assert patched3["show_pre_leetcode"] is False
    assert patched3["show_code_lab"] is True
