"""The knowledge tree — SuperMemo's unified hierarchy over decks and reading.

What matters here is that the tree is one structure spanning both kinds of
material, that a branch's priority actually reaches the scheduler, and that
structural edits can't lose study material or build a cycle.
"""

from __future__ import annotations

ARTICLE = "\n\n".join(
    f"Paragraph {i}. " + ("Spaced repetition schedules reviews just before forgetting. " * 6)
    for i in range(4)
)


def flatten(nodes: list[dict]) -> list[dict]:
    out: list[dict] = []
    for n in nodes:
        out.append(n)
        out.extend(flatten(n.get("children", [])))
    return out


def find(nodes: list[dict], **match) -> dict | None:
    for n in flatten(nodes):
        if all(n.get(k) == v for k, v in match.items()):
            return n
    return None


async def tree_of(client) -> list[dict]:
    resp = await client.get("/api/tree")
    assert resp.status_code == 200, resp.text
    return resp.json()["nodes"]


class TestBackfill:
    async def test_existing_decks_appear_without_any_migration_step(self, auth_client):
        """Registration seeds a Default deck through a path that predates the
        tree; opening the tree must still show it."""
        nodes = await tree_of(auth_client)
        default = find(nodes, kind="deck", title="Default")
        assert default is not None
        assert default["deck_id"]

    async def test_backfill_is_idempotent(self, auth_client):
        first = flatten(await tree_of(auth_client))
        second = flatten(await tree_of(auth_client))
        assert len(first) == len(second)
        assert {n["id"] for n in first} == {n["id"] for n in second}

    async def test_deck_nesting_mirrors_the_deck_tree(self, auth_client):
        parent = (await auth_client.post("/api/decks", json={"name": "Medicine"})).json()
        child = (
            await auth_client.post(
                "/api/decks", json={"name": "Pharmacology", "parent_id": parent["id"]}
            )
        ).json()

        nodes = await tree_of(auth_client)
        parent_node = find(nodes, deck_id=parent["id"])
        child_node = find(nodes, deck_id=child["id"])
        assert parent_node is not None and child_node is not None
        assert child_node["parent_id"] == parent_node["id"]


class TestReadingMaterialInTheSameTree:
    async def test_a_source_and_its_extracts_are_one_branch(self, auth_client):
        source = (
            await auth_client.post(
                "/api/sources", json={"title": "On Memory", "raw_text": ARTICLE}
            )
        ).json()
        nodes = await tree_of(auth_client)
        source_node = find(nodes, source_id=source["id"])
        assert source_node is not None
        assert source_node["kind"] == "source"
        assert len(source_node["children"]) == source["extract_count"] > 1
        assert all(c["kind"] == "extract" for c in source_node["children"])

    async def test_splitting_an_extract_nests_the_child_under_its_parent(self, auth_client):
        """The lineage the IR loop creates — previously discarded, which left
        both fragments as siblings under the source."""
        source = (
            await auth_client.post(
                "/api/sources", json={"title": "Lineage", "raw_text": ARTICLE}
            )
        ).json()
        extracts = (await auth_client.get(f"/api/sources/{source['id']}/extracts")).json()
        parent_extract = extracts[0]

        child = (
            await auth_client.post(
                f"/api/extracts/{parent_extract['id']}/split",
                json={"text": "Paragraph 0.", "priority": 90},
            )
        ).json()

        nodes = await tree_of(auth_client)
        parent_node = find(nodes, extract_id=parent_extract["id"])
        child_node = find(nodes, extract_id=child["id"])
        assert parent_node is not None and child_node is not None
        assert child_node["parent_id"] == parent_node["id"], "child should hang off its parent"

    async def test_a_source_can_be_filed_under_a_topic(self, auth_client):
        topic = (
            await auth_client.post("/api/tree/nodes", json={"title": "Neuroscience"})
        ).json()
        source = (
            await auth_client.post(
                "/api/sources",
                json={"title": "Synapses", "raw_text": ARTICLE, "parent_node_id": topic["id"]},
            )
        ).json()
        nodes = await tree_of(auth_client)
        source_node = find(nodes, source_id=source["id"])
        assert source_node["parent_id"] == topic["id"]


class TestStructure:
    async def test_topics_group_decks_and_sources_together(self, auth_client):
        topic = (await auth_client.post("/api/tree/nodes", json={"title": "Spanish"})).json()
        deck = (await auth_client.post("/api/decks", json={"name": "Verbs"})).json()
        source = (
            await auth_client.post(
                "/api/sources", json={"title": "Grammar notes", "raw_text": ARTICLE}
            )
        ).json()

        nodes = await tree_of(auth_client)
        deck_node = find(nodes, deck_id=deck["id"])
        source_node = find(nodes, source_id=source["id"])
        for node_id in (deck_node["id"], source_node["id"]):
            resp = await auth_client.post(
                f"/api/tree/nodes/{node_id}/move", json={"parent_id": topic["id"]}
            )
            assert resp.status_code == 200, resp.text

        nodes = await tree_of(auth_client)
        branch = find(nodes, id=topic["id"])
        kinds = {c["kind"] for c in branch["children"]}
        assert kinds == {"deck", "source"}, "one branch holds cards and reading alike"

    async def test_a_branch_cannot_be_moved_inside_itself(self, auth_client):
        outer = (await auth_client.post("/api/tree/nodes", json={"title": "Outer"})).json()
        inner = (
            await auth_client.post(
                "/api/tree/nodes", json={"title": "Inner", "parent_id": outer["id"]}
            )
        ).json()
        resp = await auth_client.post(
            f"/api/tree/nodes/{outer['id']}/move", json={"parent_id": inner["id"]}
        )
        assert resp.status_code == 400
        assert "inside itself" in resp.json()["detail"]

    async def test_a_node_cannot_be_its_own_parent(self, auth_client):
        node = (await auth_client.post("/api/tree/nodes", json={"title": "Self"})).json()
        resp = await auth_client.post(
            f"/api/tree/nodes/{node['id']}/move", json={"parent_id": node["id"]}
        )
        assert resp.status_code == 400

    async def test_deleting_a_topic_promotes_its_children_rather_than_eating_them(
        self, auth_client
    ):
        topic = (await auth_client.post("/api/tree/nodes", json={"title": "Doomed"})).json()
        deck = (await auth_client.post("/api/decks", json={"name": "Survivor"})).json()
        nodes = await tree_of(auth_client)
        deck_node = find(nodes, deck_id=deck["id"])
        await auth_client.post(
            f"/api/tree/nodes/{deck_node['id']}/move", json={"parent_id": topic["id"]}
        )

        resp = await auth_client.delete(f"/api/tree/nodes/{topic['id']}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["children_promoted"] == 1

        nodes = await tree_of(auth_client)
        assert find(nodes, id=topic["id"]) is None
        survivor = find(nodes, deck_id=deck["id"])
        assert survivor is not None, "the deck must outlive the topic it was filed under"
        assert survivor["parent_id"] is None

    async def test_an_entity_node_refuses_to_be_deleted_on_its_own(self, auth_client):
        deck = (await auth_client.post("/api/decks", json={"name": "Attached"})).json()
        nodes = await tree_of(auth_client)
        deck_node = find(nodes, deck_id=deck["id"])
        resp = await auth_client.delete(f"/api/tree/nodes/{deck_node['id']}")
        assert resp.status_code == 409
        assert "deck" in resp.json()["detail"]

    async def test_deleting_a_deck_does_not_take_topics_filed_under_it(self, auth_client):
        deck = (await auth_client.post("/api/decks", json={"name": "Container"})).json()
        nodes = await tree_of(auth_client)
        deck_node = find(nodes, deck_id=deck["id"])
        topic = (
            await auth_client.post(
                "/api/tree/nodes", json={"title": "Keeper", "parent_id": deck_node["id"]}
            )
        ).json()

        assert (await auth_client.delete(f"/api/decks/{deck['id']}")).status_code == 204
        nodes = await tree_of(auth_client)
        assert find(nodes, id=topic["id"]) is not None, "the FK cascade must not reach the topic"


class TestPriority:
    async def test_priority_is_inherited_from_the_nearest_ancestor(self, auth_client):
        topic = (
            await auth_client.post("/api/tree/nodes", json={"title": "Branch", "priority": 80})
        ).json()
        child = (
            await auth_client.post(
                "/api/tree/nodes", json={"title": "Leaf", "parent_id": topic["id"]}
            )
        ).json()
        nodes = await tree_of(auth_client)
        leaf = find(nodes, id=child["id"])
        assert leaf["priority"] == 80
        assert leaf["priority_inherited"] is True

    async def test_cascading_writes_the_priority_the_scheduler_actually_reads(
        self, auth_client
    ):
        """A branch sweep has to land on the entities: the composer reads deck
        and extract priority, never the node's."""
        topic = (await auth_client.post("/api/tree/nodes", json={"title": "Sweep"})).json()
        deck = (
            await auth_client.post("/api/decks", json={"name": "Swept", "default_priority": 20})
        ).json()
        nodes = await tree_of(auth_client)
        deck_node = find(nodes, deck_id=deck["id"])
        await auth_client.post(
            f"/api/tree/nodes/{deck_node['id']}/move", json={"parent_id": topic["id"]}
        )

        resp = await auth_client.patch(
            f"/api/tree/nodes/{topic['id']}", json={"priority": 95, "cascade": True}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["entities_updated"] >= 1

        decks = (await auth_client.get("/api/decks")).json()
        swept = next(d for d in decks if d["id"] == deck["id"])
        assert swept["default_priority"] == 95

    async def test_without_cascade_only_the_node_changes(self, auth_client):
        topic = (await auth_client.post("/api/tree/nodes", json={"title": "Quiet"})).json()
        deck = (
            await auth_client.post("/api/decks", json={"name": "Untouched", "default_priority": 30})
        ).json()
        nodes = await tree_of(auth_client)
        deck_node = find(nodes, deck_id=deck["id"])
        await auth_client.post(
            f"/api/tree/nodes/{deck_node['id']}/move", json={"parent_id": topic["id"]}
        )

        await auth_client.patch(f"/api/tree/nodes/{topic['id']}", json={"priority": 95})

        decks = (await auth_client.get("/api/decks")).json()
        assert next(d for d in decks if d["id"] == deck["id"])["default_priority"] == 30


class TestBranchScopedSessions:
    async def test_a_branch_session_excludes_everything_outside_it(self, auth_client):
        note_types = (await auth_client.get("/api/note-types")).json()
        basic = next(nt for nt in note_types if nt["template_kind"] == "basic")

        wanted = (await auth_client.post("/api/decks", json={"name": "Wanted"})).json()
        other = (await auth_client.post("/api/decks", json={"name": "Other"})).json()
        for deck, front in ((wanted, "in branch"), (other, "out of branch")):
            await auth_client.post(
                "/api/notes",
                json={
                    "deck_id": deck["id"],
                    "note_type_id": basic["id"],
                    "field_values": {"Front": front, "Back": "answer"},
                },
            )

        topic = (await auth_client.post("/api/tree/nodes", json={"title": "Scoped"})).json()
        nodes = await tree_of(auth_client)
        await auth_client.post(
            f"/api/tree/nodes/{find(nodes, deck_id=wanted['id'])['id']}/move",
            json={"parent_id": topic["id"]},
        )

        resp = await auth_client.get(f"/api/queue/session?branch={topic['id']}")
        assert resp.status_code == 200, resp.text
        fronts = {i["front"] for i in resp.json()["items"]}
        assert "in branch" in fronts
        assert "out of branch" not in fronts

    async def test_an_empty_branch_yields_nothing_rather_than_everything(self, auth_client):
        """The dangerous failure: an empty scope silently degrading to "all"."""
        note_types = (await auth_client.get("/api/note-types")).json()
        basic = next(nt for nt in note_types if nt["template_kind"] == "basic")
        deck = (await auth_client.get("/api/decks")).json()[0]
        await auth_client.post(
            "/api/notes",
            json={
                "deck_id": deck["id"],
                "note_type_id": basic["id"],
                "field_values": {"Front": "somewhere else", "Back": "a"},
            },
        )
        empty = (await auth_client.post("/api/tree/nodes", json={"title": "Empty"})).json()

        resp = await auth_client.get(f"/api/queue/session?branch={empty['id']}")
        assert resp.json()["items"] == []

        unscoped = await auth_client.get("/api/queue/session")
        assert len(unscoped.json()["items"]) > 0, "the same query unscoped does return cards"

    async def test_cards_carved_from_an_extract_belong_to_its_branch(self, auth_client):
        """A card's route into a branch is its deck *or* the extract it came
        from — otherwise "study this article" would miss what it produced."""
        source = (
            await auth_client.post(
                "/api/sources", json={"title": "Producer", "raw_text": ARTICLE}
            )
        ).json()
        extracts = (await auth_client.get(f"/api/sources/{source['id']}/extracts")).json()
        deck = (await auth_client.post("/api/decks", json={"name": "Elsewhere"})).json()

        await auth_client.post(
            f"/api/extracts/{extracts[0]['id']}/accept-cards",
            json={
                "deck_id": deck["id"],
                "cards": [{"kind": "basic", "front": "carved out", "back": "yes"}],
            },
        )

        nodes = await tree_of(auth_client)
        source_node = find(nodes, source_id=source["id"])
        resp = await auth_client.get(f"/api/tree/nodes/{source_node['id']}/cards")
        assert resp.status_code == 200, resp.text
        assert "carved out" in {c["front"] for c in resp.json()}

    async def test_counts_roll_up_through_the_branch(self, auth_client):
        note_types = (await auth_client.get("/api/note-types")).json()
        basic = next(nt for nt in note_types if nt["template_kind"] == "basic")
        topic = (await auth_client.post("/api/tree/nodes", json={"title": "Rollup"})).json()
        deck = (await auth_client.post("/api/decks", json={"name": "Counted"})).json()
        for i in range(3):
            await auth_client.post(
                "/api/notes",
                json={
                    "deck_id": deck["id"],
                    "note_type_id": basic["id"],
                    "field_values": {"Front": f"q{i}", "Back": "a"},
                },
            )
        nodes = await tree_of(auth_client)
        await auth_client.post(
            f"/api/tree/nodes/{find(nodes, deck_id=deck['id'])['id']}/move",
            json={"parent_id": topic["id"]},
        )

        nodes = await tree_of(auth_client)
        assert find(nodes, id=topic["id"])["card_count"] == 3


class TestTenantIsolation:
    async def test_another_users_node_is_not_reachable(self, client):
        import uuid

        async def register() -> str:
            email = f"tree-{uuid.uuid4().hex[:8]}@example.com"
            resp = await client.post(
                "/api/auth/register", json={"email": email, "password": "hunter2hunter2"}
            )
            return resp.json()["access_token"]

        alice, bob = await register(), await register()

        client.headers["Authorization"] = f"Bearer {alice}"
        secret = (await client.post("/api/tree/nodes", json={"title": "Alice only"})).json()

        client.headers["Authorization"] = f"Bearer {bob}"
        assert (await client.get(f"/api/tree/nodes/{secret['id']}/branch")).status_code == 404
        assert (
            await client.patch(f"/api/tree/nodes/{secret['id']}", json={"title": "hijacked"})
        ).status_code == 404
        assert (await client.delete(f"/api/tree/nodes/{secret['id']}")).status_code == 404
        assert (
            await client.post(f"/api/tree/nodes/{secret['id']}/move", json={"parent_id": None})
        ).status_code == 404
        assert find(await tree_of(client), id=secret["id"]) is None
