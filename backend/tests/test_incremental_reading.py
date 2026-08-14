"""Incremental Reading (§8) and the priority queue's interleaving (§9)."""

from __future__ import annotations

from app.services.ir_service import chunk_text, extract_readable

ARTICLE = "\n\n".join(
    f"Paragraph {i}. " + ("Spaced repetition schedules reviews just before forgetting. " * 6)
    for i in range(6)
)


class TestChunking:
    def test_splits_on_paragraph_boundaries(self):
        chunks = chunk_text(ARTICLE, target=500)
        assert len(chunks) > 1
        assert all(c.strip() for c in chunks)
        # No text is lost or duplicated in the split.
        assert sum(len(c.replace("\n", " ").split()) for c in chunks) == len(
            ARTICLE.replace("\n", " ").split()
        )

    def test_short_text_stays_one_chunk(self):
        assert chunk_text("Just one short paragraph.") == ["Just one short paragraph."]

    def test_oversized_paragraph_splits_on_sentences_not_mid_word(self):
        para = " ".join(f"Sentence number {i} goes here." for i in range(200))
        chunks = chunk_text(para, target=400)
        assert len(chunks) > 1
        assert all(c.endswith(".") for c in chunks)

    def test_empty_input_yields_nothing(self):
        assert chunk_text("   ") == []


class TestReadability:
    def test_strips_chrome_and_keeps_the_article(self):
        html = """
        <html><head><title>On Memory</title></head>
        <body>
          <nav>Home About Contact</nav>
          <script>tracker();</script>
          <article><p>Retrieval practice beats rereading.</p>
                   <p>Spacing beats massing.</p></article>
          <footer>© 2026</footer>
        </body></html>
        """
        title, text = extract_readable(html)
        assert title == "On Memory"
        assert "Retrieval practice beats rereading." in text
        assert "Spacing beats massing." in text
        assert "Home About Contact" not in text
        assert "tracker" not in text
        assert "© 2026" not in text


async def test_source_import_creates_staggered_extracts(auth_client):
    resp = await auth_client.post(
        "/api/sources", json={"title": "Memory article", "raw_text": ARTICLE, "priority": 70}
    )
    assert resp.status_code == 201, resp.text
    source = resp.json()
    assert source["extract_count"] > 1

    extracts = (await auth_client.get(f"/api/sources/{source['id']}/extracts")).json()
    # Only the first chunk is scheduled, so a long article can't flood the queue.
    scheduled = [e for e in extracts if e["next_shown_at"]]
    assert len(scheduled) == 1
    assert scheduled[0]["position"] == 0
    assert all(e["priority"] == 70 for e in extracts)


async def test_split_carves_a_child_and_shrinks_the_parent(auth_client):
    source = (
        await auth_client.post(
            "/api/sources",
            json={"title": "Splitting", "raw_text": "Alpha fact here. Beta fact here. Gamma fact."},
        )
    ).json()
    extracts = (await auth_client.get(f"/api/sources/{source['id']}/extracts")).json()
    parent_id = extracts[0]["id"]

    resp = await auth_client.post(
        f"/api/extracts/{parent_id}/split", json={"text": "Beta fact here.", "priority": 90}
    )
    assert resp.status_code == 201, resp.text
    child = resp.json()
    assert child["content"] == "Beta fact here."
    assert child["priority"] == 90

    parent = (await auth_client.get(f"/api/extracts/{parent_id}")).json()
    assert "Beta fact here." not in parent["content"]
    assert "Alpha fact here." in parent["content"]


async def test_split_by_character_span(auth_client):
    source = (
        await auth_client.post("/api/sources", json={"title": "Span", "raw_text": "0123456789"})
    ).json()
    parent_id = (await auth_client.get(f"/api/sources/{source['id']}/extracts")).json()[0]["id"]

    child = (
        await auth_client.post(
            f"/api/extracts/{parent_id}/split", json={"start": 2, "end": 5}
        )
    ).json()
    assert child["content"] == "234"


async def test_split_of_the_whole_extract_retires_it(auth_client):
    source = (
        await auth_client.post("/api/sources", json={"title": "All", "raw_text": "One single fact."})
    ).json()
    parent_id = (await auth_client.get(f"/api/sources/{source['id']}/extracts")).json()[0]["id"]

    await auth_client.post(f"/api/extracts/{parent_id}/split", json={"text": "One single fact."})
    parent = (await auth_client.get(f"/api/extracts/{parent_id}")).json()
    assert parent["status"] == "done"


async def test_postponing_sheds_priority(auth_client):
    source = (
        await auth_client.post(
            "/api/sources", json={"title": "Postpone", "raw_text": "Text here.", "priority": 50}
        )
    ).json()
    extract_id = (await auth_client.get(f"/api/sources/{source['id']}/extracts")).json()[0]["id"]

    resp = await auth_client.post(f"/api/extracts/{extract_id}/schedule", json={"days": 7})
    assert resp.status_code == 200
    assert resp.json()["next_shown_at"] is not None
    # Priority decays as the extract is worked (§8.4).
    assert resp.json()["priority"] == 45


async def test_accepting_generated_cards_creates_real_cards(auth_client):
    deck_id = (await auth_client.post("/api/decks", json={"name": "From reading"})).json()["id"]
    source = (
        await auth_client.post(
            "/api/sources", json={"title": "Source", "raw_text": "Ebbinghaus studied forgetting."}
        )
    ).json()
    extract_id = (await auth_client.get(f"/api/sources/{source['id']}/extracts")).json()[0]["id"]

    resp = await auth_client.post(
        f"/api/extracts/{extract_id}/accept-cards",
        json={
            "deck_id": deck_id,
            "cards": [
                {"kind": "qa", "front": "Who studied forgetting?", "back": "Ebbinghaus"},
                {
                    "kind": "cloze",
                    "front": "",
                    "back": "",
                    "cloze_text": "{{c1::Ebbinghaus}} studied forgetting.",
                },
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["cards_created"] == 2

    cards = (await auth_client.get(f"/api/cards?deck_id={deck_id}")).json()
    assert len(cards) == 2
    assert all("ir" in c["tags"] for c in cards)

    stats = (await auth_client.get("/api/stats")).json()
    assert stats["ir_throughput"]["cards_from_reading"] >= 2


async def test_card_generation_degrades_without_a_key(auth_client):
    source = (
        await auth_client.post("/api/sources", json={"title": "S", "raw_text": "Some text."})
    ).json()
    extract_id = (await auth_client.get(f"/api/sources/{source['id']}/extracts")).json()[0]["id"]

    resp = await auth_client.post(f"/api/extracts/{extract_id}/generate-cards", json={})
    assert resp.status_code == 200
    assert resp.json()["degraded"] is True
    assert resp.json()["reason"] == "consent_not_given"
    assert resp.json()["suggestions"] == []


async def test_queue_interleaves_cards_and_extracts(auth_client):
    """§9.4 — one endpoint hands back both kinds, woven rather than blocked."""
    deck_id = (await auth_client.post("/api/decks", json={"name": "Mixed"})).json()["id"]
    for i in range(6):
        await auth_client.post(
            "/api/notes",
            json={
                "deck_id": deck_id,
                "template_kind": "basic",
                "field_values": {"Front": f"Q{i}", "Back": f"A{i}"},
            },
        )
    await auth_client.post("/api/sources", json={"title": "Reading", "raw_text": ARTICLE})
    await auth_client.patch("/api/me", json={"daily_new_limit": 50, "queue_time_budget_minutes": 30})

    session = (await auth_client.get("/api/queue/session")).json()
    kinds = [i["kind"] for i in session["items"]]
    assert "card" in kinds
    assert "extract" in kinds
    # Woven, not "all cards then all extracts".
    assert kinds != sorted(kinds, key=lambda k: k == "extract")

    extract_item = next(i for i in session["items"] if i["kind"] == "extract")
    assert extract_item["extract_content"]
    assert extract_item["source_title"] == "Reading"


async def test_due_extracts_endpoint_survives_naive_timestamps(auth_client):
    """GET /api/extracts compares next_shown_at against an aware `now`, and
    SQLite returns naive datetimes even for timezone-aware columns — which
    made this endpoint raise outright rather than return a list."""
    await auth_client.post(
        "/api/sources", json={"title": "Due now", "raw_text": "First fact.\n\nSecond fact."}
    )
    resp = await auth_client.get("/api/extracts")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, list)
    # The first chunk is scheduled immediately, so it is due right now.
    assert len(body) >= 1
    assert body[0]["content"]


async def test_deleting_a_source_keeps_the_cards_it_produced(auth_client):
    deck_id = (await auth_client.post("/api/decks", json={"name": "Survivors"})).json()["id"]
    source = (
        await auth_client.post("/api/sources", json={"title": "Doomed", "raw_text": "A fact."})
    ).json()
    extract_id = (await auth_client.get(f"/api/sources/{source['id']}/extracts")).json()[0]["id"]
    await auth_client.post(
        f"/api/extracts/{extract_id}/accept-cards",
        json={"deck_id": deck_id, "cards": [{"kind": "qa", "front": "f", "back": "b"}]},
    )

    assert (await auth_client.delete(f"/api/sources/{source['id']}")).status_code == 204
    cards = (await auth_client.get(f"/api/cards?deck_id={deck_id}")).json()
    assert len(cards) == 1
