import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_tutorial_completed_defaults_and_toggle(auth_client: AsyncClient):
    # 1. Default registration: tutorial_completed must be False
    me_resp = await auth_client.get("/api/me")
    assert me_resp.status_code == 200, me_resp.text
    data = me_resp.json()
    assert data["tutorial_completed"] is False

    # 2. Toggle tutorial_completed on
    patch_resp = await auth_client.patch(
        "/api/me",
        json={"tutorial_completed": True},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    patched = patch_resp.json()
    assert patched["tutorial_completed"] is True

    # 3. Verify persistence via fresh GET /api/me
    verify_resp = await auth_client.get("/api/me")
    assert verify_resp.status_code == 200
    assert verify_resp.json()["tutorial_completed"] is True
