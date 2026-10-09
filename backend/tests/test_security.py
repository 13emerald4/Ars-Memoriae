"""Security properties: SSRF containment on URL fetching, and the multi-tenant
isolation every ownership guard is supposed to provide."""

from __future__ import annotations

import io
import uuid

import pytest

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.services.ir_service import FetchError, assert_fetchable

# ── SSRF (§8.1 fetches a URL the *user* chooses) ────────────────────────────

BLOCKED = [
    ("http://169.254.169.254/latest/meta-data/", "cloud metadata — hands out credentials"),
    ("http://metadata.google.internal/computeMetadata/v1/", "GCP metadata"),
    ("http://127.0.0.1:8000/api/export", "the app's own API"),
    ("http://localhost:5432/", "loopback"),
    ("http://[::1]/", "IPv6 loopback"),
    ("http://10.0.0.5/admin", "RFC1918"),
    ("http://192.168.1.1/", "RFC1918"),
    ("http://172.16.0.1/", "RFC1918"),
    ("http://0.0.0.0/", "unspecified"),
]


@pytest.mark.parametrize("url,why", BLOCKED)
async def test_non_public_destinations_are_refused(url, why):
    with pytest.raises(FetchError) as exc:
        await assert_fetchable(url)
    assert "non-public" in str(exc.value) or "resolve" in str(exc.value), why


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "gopher://127.0.0.1:11211/",
        "ftp://internal/",
        "javascript:alert(1)",
    ],
)
async def test_non_http_schemes_are_refused(url):
    with pytest.raises(FetchError, match="http"):
        await assert_fetchable(url)


@pytest.fixture
def fake_dns(monkeypatch):
    """Deterministic name resolution.

    The guard's whole job is deciding what a hostname resolves to, so the tests
    must control that rather than depending on the runner having DNS (or on
    example.com's address never changing).
    """
    import socket as _socket

    mapping = {"example.com": "93.184.216.34", "evil.test": "10.1.2.3"}
    # Captured before patching: ir_service.socket *is* the global socket
    # module, so a fallback that goes through the module attribute would call
    # this stub again and recurse.
    real_getaddrinfo = _socket.getaddrinfo

    def getaddrinfo(host, port, *args, **kwargs):
        if host in mapping:
            return [(_socket.AF_INET, _socket.SOCK_STREAM, 6, "", (mapping[host], port or 80))]
        return real_getaddrinfo(host, port, *args, **kwargs)

    monkeypatch.setattr("app.services.ir_service.socket.getaddrinfo", getaddrinfo)
    return mapping


async def test_public_destination_is_allowed(fake_dns):
    # No request is made by assert_fetchable — it only judges the destination.
    await assert_fetchable("https://example.com/article")


async def test_a_public_name_resolving_to_a_private_address_is_refused(fake_dns):
    """DNS is attacker-controlled: a perfectly ordinary-looking hostname can
    point at 10.x. Blocking by name would miss this; blocking by resolved
    address does not."""
    with pytest.raises(FetchError, match="non-public"):
        await assert_fetchable("http://evil.test/")


async def test_operator_can_opt_into_intranet_fetching(monkeypatch):
    """A self-hoster fetching their own wiki is a real use case — but it has to
    be a deliberate choice, not the default."""
    monkeypatch.setattr(settings, "url_fetch_allow_private", True)
    await assert_fetchable("http://192.168.1.50/wiki/page")


async def test_fetching_can_be_disabled_entirely(monkeypatch):
    monkeypatch.setattr(settings, "url_fetch_enabled", False)
    with pytest.raises(FetchError, match="disabled"):
        await assert_fetchable("https://example.com/")


async def test_redirects_are_revalidated_per_hop(monkeypatch, fake_dns):
    """The bug this guards: validating only the submitted URL lets a public
    page 302 the server straight to the metadata endpoint."""
    from app.services import ir_service

    seen: list[str] = []

    async def spy(url: str) -> None:
        seen.append(url)
        await assert_fetchable(url)

    monkeypatch.setattr(ir_service, "assert_fetchable", spy)

    import types

    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "example.com":
            return httpx.Response(302, headers={"location": "http://169.254.169.254/creds"})
        return httpx.Response(200, text="<html><body><p>secrets</p></body></html>")

    transport = httpx.MockTransport(handler)

    # Swap the module's view of httpx for a shim whose AsyncClient is bound to
    # a mock transport. Patching the real class in place recurses, because the
    # replacement ends up calling itself.
    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return httpx.AsyncClient(*args, **kwargs)

    monkeypatch.setattr(
        ir_service,
        "httpx",
        types.SimpleNamespace(
            AsyncClient=client_factory, URL=httpx.URL, HTTPError=httpx.HTTPError
        ),
    )

    with pytest.raises(FetchError) as exc:
        await ir_service.fetch_url("http://example.com/start")

    assert "non-public" in str(exc.value)
    assert seen == ["http://example.com/start", "http://169.254.169.254/creds"]


async def test_source_endpoint_surfaces_a_blocked_fetch_as_400(auth_client):
    resp = await auth_client.post(
        "/api/sources", json={"url": "http://169.254.169.254/latest/meta-data/"}
    )
    assert resp.status_code == 400
    assert "could not fetch" in resp.json()["detail"]


# ── multi-tenant isolation ──────────────────────────────────────────────────


@pytest.fixture
async def two_users(client):
    """Two separate accounts, each with a deck, note, card and IR source."""

    async def make(tag: str) -> dict:
        email = f"{tag}-{uuid.uuid4().hex[:8]}@example.com"
        token = (
            await client.post(
                "/api/auth/register", json={"email": email, "password": "hunter2hunter2"}
            )
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        deck = (
            await client.post("/api/decks", json={"name": f"{tag} deck"}, headers=headers)
        ).json()
        note = (
            await client.post(
                "/api/notes",
                json={
                    "deck_id": deck["id"],
                    "template_kind": "basic",
                    "field_values": {"Front": f"{tag} secret front", "Back": f"{tag} secret back"},
                },
                headers=headers,
            )
        ).json()
        source = (
            await client.post(
                "/api/sources",
                json={"title": f"{tag} source", "raw_text": f"{tag} private reading material."},
                headers=headers,
            )
        ).json()
        extract = (
            await client.get(f"/api/sources/{source['id']}/extracts", headers=headers)
        ).json()[0]
        nt = (await client.get("/api/note-types", headers=headers)).json()[0]

        return {
            "headers": headers,
            "deck": deck,
            "note": note,
            "card": note["cards"][0],
            "source": source,
            "extract": extract,
            "note_type": nt,
        }

    alice = await make("alice")
    bob = await make("bob")
    client.headers.pop("Authorization", None)
    return alice, bob


async def test_listings_never_leak_across_accounts(client, two_users):
    _alice, bob = two_users

    decks = (await client.get("/api/decks", headers=bob["headers"])).json()
    assert all(d["name"] != "alice deck" for d in decks)

    cards = (await client.get("/api/cards?limit=200", headers=bob["headers"])).json()
    assert all("alice" not in c["front"] for c in cards)

    sources = (await client.get("/api/sources", headers=bob["headers"])).json()
    assert all(s["title"] != "alice source" for s in sources)

    export = (await client.get("/api/export", headers=bob["headers"])).json()
    assert "alice secret" not in str(export)


@pytest.mark.parametrize(
    "method,path_key,template",
    [
        ("GET", "note", "/api/notes/{id}"),
        ("PATCH", "note", "/api/notes/{id}"),
        ("DELETE", "note", "/api/notes/{id}"),
        ("PATCH", "deck", "/api/decks/{id}"),
        ("DELETE", "deck", "/api/decks/{id}"),
        ("POST", "card", "/api/cards/{id}/suspend"),
        ("POST", "card", "/api/review/{id}/answer"),
        ("POST", "card", "/api/review/{id}/confirm"),
        ("GET", "source", "/api/sources/{id}/extracts"),
        ("DELETE", "source", "/api/sources/{id}"),
        ("GET", "extract", "/api/extracts/{id}"),
        ("POST", "extract", "/api/extracts/{id}/split"),
        ("POST", "extract", "/api/extracts/{id}/schedule"),
        ("POST", "extract", "/api/extracts/{id}/generate-cards"),
    ],
)
async def test_bobs_token_cannot_touch_alices_objects(client, two_users, method, path_key, template):
    alice, bob = two_users
    path = template.format(id=alice[path_key]["id"])

    bodies = {
        "/api/review/{id}/answer": {"typed_answer": "x", "latency_ms": 1},
        "/api/review/{id}/confirm": {"final_grade": "good", "overridden": False},
        "/api/extracts/{id}/split": {"text": "alice private"},
        "/api/extracts/{id}/schedule": {"days": 1},
        "/api/extracts/{id}/generate-cards": {},
        "/api/notes/{id}": {"field_values": {"Front": "hacked", "Back": "hacked"}},
        "/api/decks/{id}": {"name": "hacked"},
    }
    resp = await client.request(
        method, path, headers=bob["headers"], json=bodies.get(template)
    )
    assert resp.status_code == 404, f"{method} {template} leaked: {resp.status_code} {resp.text}"


async def test_cannot_plant_a_note_in_another_users_deck(client, two_users):
    alice, bob = two_users
    resp = await client.post(
        "/api/notes",
        json={
            "deck_id": alice["deck"]["id"],
            "template_kind": "basic",
            "field_values": {"Front": "planted", "Back": "planted"},
        },
        headers=bob["headers"],
    )
    assert resp.status_code == 404


async def test_cannot_borrow_another_users_note_type(client, two_users):
    alice, bob = two_users
    bob_deck = (await client.get("/api/decks", headers=bob["headers"])).json()[0]
    resp = await client.post(
        "/api/notes",
        json={
            "deck_id": bob_deck["id"],
            "note_type_id": alice["note_type"]["id"],
            "field_values": {"Front": "x", "Back": "y"},
        },
        headers=bob["headers"],
    )
    assert resp.status_code == 404


@pytest.mark.parametrize("target", ["deck", "card", "source", "extract"])
async def test_priority_endpoint_enforces_ownership(client, two_users, target):
    alice, bob = two_users
    resp = await client.patch(
        "/api/priority",
        json={"target": target, "id": alice[target]["id"], "priority": 99},
        headers=bob["headers"],
    )
    assert resp.status_code == 404


async def test_interference_scan_only_sees_your_own_notes(client, two_users):
    _alice, bob = two_users
    scan = (await client.post("/api/interference/scan", headers=bob["headers"])).json()
    # Bob has exactly one note; Alice's must not be in the corpus.
    assert scan["notes_scanned"] == 1


async def test_leech_actions_enforce_ownership(client, two_users):
    alice, bob = two_users
    for action in ("dismiss", "suspend", "accept"):
        resp = await client.post(
            f"/api/leeches/{alice['card']['id']}/{action}", headers=bob["headers"]
        )
        assert resp.status_code == 404


# ── credentials & secrets ───────────────────────────────────────────────────


class TestCredentials:
    def test_password_hashes_are_salted(self):
        a, b = hash_password("same-password"), hash_password("same-password")
        assert a != b, "identical passwords must not produce identical hashes"
        assert verify_password("same-password", a)
        assert verify_password("same-password", b)

    def test_wrong_password_rejected(self):
        assert not verify_password("wrong", hash_password("right"))

    def test_malformed_hash_does_not_crash(self):
        for stored in ("", "garbage", "scrypt$bad", "md5$1$2$3$4$5"):
            assert verify_password("x", stored) is False


async def test_expired_or_forged_tokens_are_rejected(client):
    import jwt

    client.headers.pop("Authorization", None)
    forged = jwt.encode({"sub": str(uuid.uuid4()), "exp": 9999999999}, "wrong-key", algorithm="HS256")
    resp = await client.get("/api/decks", headers={"Authorization": f"Bearer {forged}"})
    assert resp.status_code == 401


async def test_upload_size_and_type_limits(auth_client):
    # A .png name with a script payload is still rejected on declared type.
    resp = await auth_client.post(
        "/api/media",
        files={"file": ("x.php", io.BytesIO(b"<?php system($_GET[0]); ?>"), "application/x-php")},
    )
    assert resp.status_code == 415


# ── SPA fallback route: no escaping the frontend build directory ────────────


@pytest.fixture
def fake_dist(tmp_path, monkeypatch):
    import app.main

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>spa</html>")
    (dist / "robots.txt").write_text("User-agent: *")
    (tmp_path / "secret.env").write_text("SECRET_KEY=leaked")
    monkeypatch.setattr(app.main, "_frontend_dist", dist)
    return dist


@pytest.mark.parametrize(
    "path",
    ["/..%2fsecret.env", "/%2e%2e%2fsecret.env", "/robots.txt%2f..%2f..%2fsecret.env"],
)
async def test_spa_route_does_not_serve_files_outside_the_build(client, fake_dist, path):
    resp = await client.get(path)
    assert "leaked" not in resp.text
    # Falls through to the SPA shell like any other unknown route.
    assert resp.text == "<html>spa</html>"


async def test_spa_route_still_serves_real_build_files(client, fake_dist):
    resp = await client.get("/robots.txt")
    assert resp.status_code == 200
    assert resp.text == "User-agent: *"


# ── sign-up closes once the instance has an account ─────────────────────────


async def test_registration_closes_after_the_first_account(client, monkeypatch):
    # Make sure at least one account exists, whatever ran before this test.
    await client.post(
        "/api/auth/register", json={"email": "owner@example.com", "password": "pw-123456"}
    )
    monkeypatch.setattr(settings, "allow_registration", False)

    resp = await client.post(
        "/api/auth/register", json={"email": "stranger@example.com", "password": "pw-123456"}
    )
    assert resp.status_code == 403
    assert "ALLOW_REGISTRATION" in resp.json()["detail"]

    # Existing accounts can still sign in.
    login = await client.post(
        "/api/auth/login", json={"email": "owner@example.com", "password": "pw-123456"}
    )
    assert login.status_code == 200


async def test_first_account_can_always_register(monkeypatch):
    """An empty instance must accept its owner even with sign-up closed."""
    from app.routers.auth import registration_open

    monkeypatch.setattr(settings, "allow_registration", False)

    class FakeDb:
        def __init__(self, first_user_id):
            self.first_user_id = first_user_id

        async def scalar(self, _stmt):
            return self.first_user_id

    assert await registration_open(FakeDb(None)) is True
    assert await registration_open(FakeDb(uuid.uuid4())) is False

    monkeypatch.setattr(settings, "allow_registration", True)
    assert await registration_open(FakeDb(uuid.uuid4())) is True
