from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

TMP = Path(tempfile.mkdtemp(prefix="memapp-tests-"))
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{TMP / 'test.db'}")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("MEDIA_ROOT", str(TMP / "media"))
os.environ.setdefault("ENABLE_BACKGROUND_JOBS", "0")
# Most tests need several accounts; the closed default is tested explicitly.
os.environ.setdefault("ALLOW_REGISTRATION", "1")

import httpx
from asgi_lifespan import LifespanManager  # type: ignore

from app.db import Base, engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
async def _schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest.fixture
async def client():
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


@pytest.fixture
async def auth_client(client):
    """A registered, logged-in user with the starter deck/note types."""
    import uuid

    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    resp = await client.post(
        "/api/auth/register", json={"email": email, "password": "hunter2hunter2"}
    )
    assert resp.status_code == 201, resp.text
    client.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"
    return client
