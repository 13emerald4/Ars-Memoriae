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

