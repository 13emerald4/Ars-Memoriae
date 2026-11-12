"""Tests for deleting all in the knowledge tree and individual tree node deletions."""

from __future__ import annotations

ARTICLE = "Paragraph 1. Spaced repetition is effective for long term retention."


async def tree_of(client) -> list[dict]:
    resp = await client.get("/api/tree")
    assert resp.status_code == 200, resp.text
    return resp.json()["nodes"]


class TestDeleteTree:
    async def test_delete_all_clears_topics_sources_and_decks(self, auth_client):
        # 1. Add topic
        await auth_client.post("/api/tree/nodes", json={"title": "Custom Topic"})
        # 2. Add source
        await auth_client.post(
            "/api/sources", json={"title": "Custom Source", "raw_text": ARTICLE}
        )
        # 3. Add deck
        await auth_client.post("/api/decks", json={"name": "Custom Deck"})

        # Verify tree has items
        nodes_before = await tree_of(auth_client)
        assert len(nodes_before) >= 3

        # Call DELETE /api/tree
        del_resp = await auth_client.delete("/api/tree")
        assert del_resp.status_code == 200
        data = del_resp.json()
        assert data["deleted"] is True
        assert data["summary"]["sources"] >= 1
        assert data["summary"]["decks"] >= 1

        # Tree is now completely empty
        nodes_after = await tree_of(auth_client)
        assert len(nodes_after) == 0

    async def test_delete_source_and_extract(self, auth_client):
        src = (
            await auth_client.post(
                "/api/sources", json={"title": "Source With Extracts", "raw_text": ARTICLE}
            )
        ).json()
        extracts = (await auth_client.get(f"/api/sources/{src['id']}/extracts")).json()
        assert len(extracts) > 0
        ext_id = extracts[0]["id"]

        # Delete single extract
        del_ext = await auth_client.delete(f"/api/extracts/{ext_id}")
        assert del_ext.status_code == 204

        # Delete source
        del_src = await auth_client.delete(f"/api/sources/{src['id']}")
        assert del_src.status_code == 204

    async def test_duplicate_source_prevention(self, auth_client):
        src1 = (
            await auth_client.post(
                "/api/sources", json={"title": "Unique Title", "raw_text": ARTICLE}
            )
        ).json()
        src2 = (
            await auth_client.post(
                "/api/sources", json={"title": "Unique Title", "raw_text": ARTICLE}
            )
        ).json()
        assert src1["id"] == src2["id"]

    async def test_delete_deck_with_hierarchical_subdecks_and_cards(self, auth_client):
        # 1. Create parent deck
        p_resp = await auth_client.post("/api/decks", json={"name": "Parent Root Deck"})
        assert p_resp.status_code == 201
        parent_id = p_resp.json()["id"]

        # 2. Create child subdeck
        c_resp = await auth_client.post(
            "/api/decks", json={"name": "Child Subdeck", "parent_id": parent_id}
        )
        assert c_resp.status_code == 201
        child_id = c_resp.json()["id"]

        # 3. Add note and card to child subdeck
        nt_resp = await auth_client.get("/api/note-types")
        assert nt_resp.status_code == 200
        nt_id = nt_resp.json()[0]["id"]

        note_resp = await auth_client.post(
            "/api/notes",
            json={
                "deck_id": child_id,
                "note_type_id": nt_id,
                "field_values": {"front": "Subdeck Question", "back": "Subdeck Answer"},
            },
        )
        assert note_resp.status_code == 201

        # 4. Without cascade, deleting parent deck should 409 Conflict
        no_casc = await auth_client.delete(f"/api/decks/{parent_id}?cascade=false")
        assert no_casc.status_code == 409

        # 5. With cascade=true, parent deck, subdeck, and cards are deleted cleanly
        del_resp = await auth_client.delete(f"/api/decks/{parent_id}?cascade=true")
        assert del_resp.status_code == 204

        # 6. Verify decks are gone
        decks_resp = await auth_client.get("/api/decks")
        deck_ids = [d["id"] for d in decks_resp.json()]
        assert parent_id not in deck_ids
        assert child_id not in deck_ids

