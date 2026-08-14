"""Mastery gating — Alpha-School-style prerequisite locks on the tree.

A node can require another node's subtree to reach a mastery percentage
before its own cards enter the queue. What matters here: the gate is real
(locked cards genuinely never reach the composer, cards and reading alike),
cycles are refused rather than silently accepted, and a user who never
touches this feature pays nothing for it.
"""

from __future__ import annotations


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


async def _deck(client, name: str) -> dict:
    resp = await client.post("/api/decks", json={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _card(client, deck_id: str, front: str = "q", back: str = "a") -> str:
    note_types = (await client.get("/api/note-types")).json()
    basic = next(nt for nt in note_types if nt["template_kind"] == "basic")
    resp = await client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "note_type_id": basic["id"],
            "field_values": {"Front": front, "Back": back},
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["cards"][0]["id"]


async def _graduate(client, card_id: str) -> None:
    """Push a card from new -> learning -> review, matching the FSRS graduation
    path already pinned in test_review_loop.py: two "good"s in a row."""
    for _ in range(2):
        resp = await client.post(
            f"/api/review/{card_id}/confirm", json={"final_grade": "good", "overridden": False}
        )
        assert resp.status_code == 200, resp.text


async def _deck_node(client, deck_id: str) -> dict:
    return find(await tree_of(client), deck_id=deck_id)


class TestPrerequisiteValidation:
    async def test_a_node_cannot_require_itself(self, auth_client):
        node = (await auth_client.post("/api/tree/nodes", json={"title": "Loop"})).json()
        resp = await auth_client.patch(
            f"/api/tree/nodes/{node['id']}", json={"requires_node_id": node["id"]}
        )
        assert resp.status_code == 400
        assert "itself" in resp.json()["detail"]

    async def test_a_two_node_cycle_is_refused(self, auth_client):
        a = (await auth_client.post("/api/tree/nodes", json={"title": "A"})).json()
        b = (await auth_client.post("/api/tree/nodes", json={"title": "B"})).json()

        first = await auth_client.patch(
            f"/api/tree/nodes/{a['id']}", json={"requires_node_id": b["id"]}
        )
        assert first.status_code == 200, first.text

        second = await auth_client.patch(
            f"/api/tree/nodes/{b['id']}", json={"requires_node_id": a["id"]}
        )
        assert second.status_code == 400
        assert "cycle" in second.json()["detail"]

    async def test_a_three_node_cycle_is_refused(self, auth_client):
        a = (await auth_client.post("/api/tree/nodes", json={"title": "A"})).json()
        b = (await auth_client.post("/api/tree/nodes", json={"title": "B"})).json()
        c = (await auth_client.post("/api/tree/nodes", json={"title": "C"})).json()
        await auth_client.patch(f"/api/tree/nodes/{a['id']}", json={"requires_node_id": b["id"]})
        await auth_client.patch(f"/api/tree/nodes/{b['id']}", json={"requires_node_id": c["id"]})

        resp = await auth_client.patch(
            f"/api/tree/nodes/{c['id']}", json={"requires_node_id": a["id"]}
        )
        assert resp.status_code == 400
        assert "cycle" in resp.json()["detail"]

    async def test_a_genuine_multi_level_chain_is_allowed(self, auth_client):
        """A -> B -> C is a real prerequisite chain, not a cycle — must not be
        rejected just because it's more than one hop."""
        a = (await auth_client.post("/api/tree/nodes", json={"title": "Calculus"})).json()
        b = (await auth_client.post("/api/tree/nodes", json={"title": "Algebra"})).json()
        c = (await auth_client.post("/api/tree/nodes", json={"title": "Arithmetic"})).json()
        r1 = await auth_client.patch(
            f"/api/tree/nodes/{a['id']}", json={"requires_node_id": b["id"]}
        )
        r2 = await auth_client.patch(
            f"/api/tree/nodes/{b['id']}", json={"requires_node_id": c["id"]}
        )
        assert r1.status_code == 200, r1.text
        assert r2.status_code == 200, r2.text

    async def test_a_source_cannot_be_gated_or_be_a_prerequisite(self, auth_client):
        await auth_client.post(
            "/api/sources", json={"title": "Article", "raw_text": "Some reading material."}
        )
        topic = (await auth_client.post("/api/tree/nodes", json={"title": "T"})).json()
        nodes = await tree_of(auth_client)
        source_node = find(nodes, kind="source")

        gated = await auth_client.patch(
            f"/api/tree/nodes/{source_node['id']}", json={"requires_node_id": topic["id"]}
        )
        assert gated.status_code == 400

        as_prereq = await auth_client.patch(
            f"/api/tree/nodes/{topic['id']}", json={"requires_node_id": source_node["id"]}
        )
        assert as_prereq.status_code == 400

    async def test_clearing_the_prerequisite_unlocks_immediately(self, auth_client):
        gate = (await auth_client.post("/api/tree/nodes", json={"title": "Gate"})).json()
        deck = await _deck(auth_client, "Gated")
        deck_node = await _deck_node(auth_client, deck["id"])
        await auth_client.patch(
            f"/api/tree/nodes/{deck_node['id']}",
            json={"requires_node_id": gate["id"], "mastery_threshold": 90},
        )
        assert (await _deck_node(auth_client, deck["id"]))["locked"] is True

        resp = await auth_client.patch(
            f"/api/tree/nodes/{deck_node['id']}", json={"requires_node_id": None}
        )
        assert resp.status_code == 200, resp.text
        assert (await _deck_node(auth_client, deck["id"]))["locked"] is False

    async def test_threshold_only_update_leaves_the_gate_alone(self, auth_client):
        gate = (await auth_client.post("/api/tree/nodes", json={"title": "Gate"})).json()
        deck = await _deck(auth_client, "Gated")
        deck_node = await _deck_node(auth_client, deck["id"])
        await auth_client.patch(
            f"/api/tree/nodes/{deck_node['id']}", json={"requires_node_id": gate["id"]}
        )

        resp = await auth_client.patch(
            f"/api/tree/nodes/{deck_node['id']}", json={"mastery_threshold": 75}
        )
        assert resp.status_code == 200, resp.text
        node = await _deck_node(auth_client, deck["id"])
        assert node["requires_node_id"] == gate["id"]
        assert node["mastery_threshold"] == 75


class TestMasteryComputation:
    async def test_an_empty_deck_has_zero_mastery(self, auth_client):
        deck = await _deck(auth_client, "Empty")
        node = await _deck_node(auth_client, deck["id"])
        assert node["mastery_pct"] == 0

    async def test_mastery_is_graduated_cards_over_total(self, auth_client):
        deck = await _deck(auth_client, "Mixed")
        graduated = await _card(auth_client, deck["id"], "q1", "a1")
        await _card(auth_client, deck["id"], "q2", "a2")  # stays new
        await _graduate(auth_client, graduated)

        node = await _deck_node(auth_client, deck["id"])
        assert node["mastery_pct"] == 50

    async def test_suspended_cards_are_excluded_from_both_sides(self, auth_client):
        deck = await _deck(auth_client, "WithSuspended")
        graduated = await _card(auth_client, deck["id"], "q1", "a1")
        suspended = await _card(auth_client, deck["id"], "q2", "a2")
        await _graduate(auth_client, graduated)
        await auth_client.post(f"/api/cards/{suspended}/suspend?suspended=true")

        node = await _deck_node(auth_client, deck["id"])
        assert node["mastery_pct"] == 100

    async def test_mastery_rolls_up_through_a_topic(self, auth_client):
        topic = (await auth_client.post("/api/tree/nodes", json={"title": "Unit"})).json()
        d1 = await _deck(auth_client, "Part1")
        d2 = await _deck(auth_client, "Part2")
        for deck in (d1, d2):
            node = await _deck_node(auth_client, deck["id"])
            await auth_client.post(
                f"/api/tree/nodes/{node['id']}/move", json={"parent_id": topic["id"]}
            )
        g1 = await _card(auth_client, d1["id"])
        await _card(auth_client, d1["id"], "q2", "a2")
        await _graduate(auth_client, g1)
        g2 = await _card(auth_client, d2["id"])
        await _graduate(auth_client, g2)

        nodes = await tree_of(auth_client)
        topic_view = find(nodes, id=topic["id"])
        # 2 of 3 cards across the whole subtree have graduated.
        assert topic_view["mastery_pct"] == 67


class TestLockingExcludesFromTheQueue:
    async def test_a_locked_decks_cards_never_reach_the_session(self, auth_client):
        gate = (await auth_client.post("/api/tree/nodes", json={"title": "Gate"})).json()
        locked_deck = await _deck(auth_client, "Locked")
        locked_node = await _deck_node(auth_client, locked_deck["id"])
        await auth_client.patch(
            f"/api/tree/nodes/{locked_node['id']}",
            json={"requires_node_id": gate["id"], "mastery_threshold": 90},
        )
        await _card(auth_client, locked_deck["id"], "locked front", "a")

        open_deck = await _deck(auth_client, "Open")
        await _card(auth_client, open_deck["id"], "open front", "a")

        session = (await auth_client.get("/api/queue/session?preview=200")).json()
        fronts = {i["front"] for i in session["items"] if i["kind"] == "card"}
        assert "open front" in fronts
        assert "locked front" not in fronts
        assert any("mastery gate" in n for n in session["notes"])

    async def test_new_cards_in_a_locked_deck_are_excluded_from_the_new_cap_too(self, auth_client):
        """Not just due reviews — new-card intake must respect the gate too,
        or a locked deck would still surface as "new" material to learn."""
        gate = (await auth_client.post("/api/tree/nodes", json={"title": "Gate"})).json()
        locked_deck = await _deck(auth_client, "LockedNew")
        locked_node = await _deck_node(auth_client, locked_deck["id"])
        await auth_client.patch(
            f"/api/tree/nodes/{locked_node['id']}", json={"requires_node_id": gate["id"]}
        )
        await _card(auth_client, locked_deck["id"], "never shown", "a")
        await auth_client.patch("/api/me", json={"daily_new_limit": 50})

        session = (await auth_client.get("/api/queue/session?preview=200")).json()
        fronts = {i["front"] for i in session["items"] if i["kind"] == "card"}
        assert "never shown" not in fronts

    async def test_locking_a_topic_locks_reading_material_under_it_too(self, auth_client):
        """"This whole unit is locked" has to mean the source material behind
        it as well, not just the flashcards."""
        gate = (await auth_client.post("/api/tree/nodes", json={"title": "Gate"})).json()
        topic = (await auth_client.post("/api/tree/nodes", json={"title": "Unit"})).json()
        await auth_client.patch(
            f"/api/tree/nodes/{topic['id']}", json={"requires_node_id": gate["id"]}
        )
        source = (
            await auth_client.post(
                "/api/sources",
                json={
                    "title": "Locked reading",
                    "raw_text": "Paragraph one.\n\nParagraph two here for good measure.",
                    "parent_node_id": topic["id"],
                },
            )
        ).json()
        assert source["active_extract_count"] > 0

        session = (await auth_client.get("/api/queue/session?preview=200")).json()
        assert not any(i["kind"] == "extract" for i in session["items"])

    async def test_meeting_the_threshold_unlocks_the_gated_deck(self, auth_client):
        gate_deck = await _deck(auth_client, "Prereq")
        card = await _card(auth_client, gate_deck["id"])
        gate_node = await _deck_node(auth_client, gate_deck["id"])

        gated_deck = await _deck(auth_client, "Downstream")
        gated_node = await _deck_node(auth_client, gated_deck["id"])
        await auth_client.patch(
            f"/api/tree/nodes/{gated_node['id']}",
            json={"requires_node_id": gate_node["id"], "mastery_threshold": 90},
        )
        await _card(auth_client, gated_deck["id"], "downstream front", "a")

        # Not yet mastered: still locked, still excluded.
        assert (await _deck_node(auth_client, gated_deck["id"]))["locked"] is True
        session = (await auth_client.get("/api/queue/session?preview=200")).json()
        assert "downstream front" not in {
            i["front"] for i in session["items"] if i["kind"] == "card"
        }

        await _graduate(auth_client, card)

        assert (await _deck_node(auth_client, gated_deck["id"]))["locked"] is False
        session = (await auth_client.get("/api/queue/session?preview=200")).json()
        assert "downstream front" in {
            i["front"] for i in session["items"] if i["kind"] == "card"
        }

    async def test_an_unlocked_prerequisite_locks_its_dependent_transitively(self, auth_client):
        """A needs B, B needs C. C is never mastered, so B can never
        accumulate reviews, so B's mastery is genuinely stuck at 0% and A
        stays locked too — with no extra propagation logic required."""
        c_deck = await _deck(auth_client, "C")
        await _card(auth_client, c_deck["id"])
        c_node = await _deck_node(auth_client, c_deck["id"])

        b_deck = await _deck(auth_client, "B")
        await _card(auth_client, b_deck["id"])
        b_node = await _deck_node(auth_client, b_deck["id"])
        await auth_client.patch(
            f"/api/tree/nodes/{b_node['id']}", json={"requires_node_id": c_node["id"]}
        )

        a_deck = await _deck(auth_client, "A")
        a_node = await _deck_node(auth_client, a_deck["id"])
        await auth_client.patch(
            f"/api/tree/nodes/{a_node['id']}", json={"requires_node_id": b_node["id"]}
        )

        assert (await _deck_node(auth_client, b_deck["id"]))["locked"] is True
        assert (await _deck_node(auth_client, a_deck["id"]))["locked"] is True

    async def test_an_ungated_user_sees_no_behavior_change(self, auth_client):
        """The regression that matters most: a user who never touches gating
        must get exactly the old, unfiltered queue."""
        deck = await _deck(auth_client, "Plain")
        await _card(auth_client, deck["id"], "plain front", "a")
        session = (await auth_client.get("/api/queue/session?preview=200")).json()
        fronts = {i["front"] for i in session["items"] if i["kind"] == "card"}
        assert "plain front" in fronts
        assert not any("mastery gate" in n for n in session["notes"])


class TestTenantIsolation:
    async def test_cannot_gate_a_node_behind_another_users_node(self, client):
        import uuid

        async def register() -> str:
            email = f"gate-{uuid.uuid4().hex[:8]}@example.com"
            resp = await client.post(
                "/api/auth/register", json={"email": email, "password": "hunter2hunter2"}
            )
            return resp.json()["access_token"]

        alice, bob = await register(), await register()

        client.headers["Authorization"] = f"Bearer {alice}"
        secret = (await client.post("/api/tree/nodes", json={"title": "Alice's"})).json()

        client.headers["Authorization"] = f"Bearer {bob}"
        mine = (await client.post("/api/tree/nodes", json={"title": "Bob's"})).json()
        resp = await client.patch(
            f"/api/tree/nodes/{mine['id']}", json={"requires_node_id": secret["id"]}
        )
        assert resp.status_code == 404
