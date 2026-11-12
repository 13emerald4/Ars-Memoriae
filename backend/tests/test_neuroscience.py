"""Neuroscience enhancements tests:
- Schema Checkpoints (mPFC foundational scaffolding) & User Settings Toggle
- Spatial Memory Palace (Entorhinal Grid / Hippocampal Place Cells) & Auto-Palace
- Associative Network (Collins & Loftus Spreading Activation)
- Dynamic Prompt Mutation (Reconsolidation Variant Cueing)
- Pre-Test Hypothesis & Prediction Error Evaluation
- Mnemonic Vignette Synthesis (Dual Coding & Von Restorff)
- Dentate Gyrus Pattern Separation Contrast Drill
"""

from __future__ import annotations

import pytest


async def _deck(client, name="Neuroscience Deck", priority=50):
    resp = await client.post("/api/decks", json={"name": name, "default_priority": priority})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _note(client, deck_id, front, back, **kw):
    resp = await client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {"Front": front, "Back": back},
            **kw,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_user_neuroscience_settings_toggle(auth_client):
    """Confirm user can toggle Schema Checkpoints, Prompt Mutation, and Prediction Mode."""
    me = (await auth_client.get("/api/me")).json()
    assert me["enable_schema_checkpoints"] is True
    assert me["enable_prompt_mutation"] is False
    assert me["enable_prediction_mode"] is False

    # Toggle Schema Checkpoints OFF and Prediction Mode ON
    update_resp = await auth_client.patch(
        "/api/me",
        json={
            "enable_schema_checkpoints": False,
            "enable_prediction_mode": True,
            "enable_prompt_mutation": True,
        },
    )
    assert update_resp.status_code == 200, update_resp.text
    updated = update_resp.json()
    assert updated["enable_schema_checkpoints"] is False
    assert updated["enable_prediction_mode"] is True
    assert updated["enable_prompt_mutation"] is True

    # Confirm persistence
    me_after = (await auth_client.get("/api/me")).json()
    assert me_after["enable_schema_checkpoints"] is False
    assert me_after["enable_prediction_mode"] is True
    assert me_after["enable_prompt_mutation"] is True


@pytest.mark.asyncio
async def test_card_neuro_props_update(auth_client):
    """Test updating schema checkpoint, locus coordinates, and mnemonic vignette."""
    deck_id = await _deck(auth_client, "Memory Palace Deck")
    note = await _note(auth_client, deck_id, "What is Bayes Theorem?", "P(A|B) = P(B|A)P(A)/P(B)")
    card_id = note["cards"][0]["id"]

    patch_resp = await auth_client.patch(
        f"/api/cards/{card_id}/neuro-props",
        json={
            "is_schema_checkpoint": True,
            "spatial_locus": "Library of Epistemology - Stanza 4",
            "spatial_x": 10.5,
            "spatial_y": 20.0,
            "mnemonic_vignette": "Thomas Bayes rolling glowing blue dice into a giant crystal chalice.",
        },
    )
    assert patch_resp.status_code == 200, patch_resp.text
    card_data = patch_resp.json()
    assert card_data["is_schema_checkpoint"] is True
    assert card_data["spatial_locus"] == "Library of Epistemology - Stanza 4"
    assert card_data["spatial_x"] == 10.5
    assert card_data["spatial_y"] == 20.0
    assert "Thomas Bayes" in card_data["mnemonic_vignette"]


@pytest.mark.asyncio
async def test_auto_palace_generation(auth_client):
    """Test auto-generating virtual memory palace layout for deck cards."""
    deck_id = await _deck(auth_client, "Algorithms Deck")
    await _note(auth_client, deck_id, "Card 1", "Ans 1")
    await _note(auth_client, deck_id, "Card 2", "Ans 2")
    await _note(auth_client, deck_id, "Card 3", "Ans 3")

    palace_resp = await auth_client.post(f"/api/decks/{deck_id}/auto-palace")
    assert palace_resp.status_code == 200, palace_resp.text
    palace_cards = palace_resp.json()
    assert len(palace_cards) == 3
    for c in palace_cards:
        assert c["spatial_locus"] is not None
        assert " · " in c["spatial_locus"] or " - " in c["spatial_locus"]
        assert c["spatial_x"] is not None
        assert c["spatial_y"] is not None


@pytest.mark.asyncio
async def test_schema_checkpoint_queue_priority_boost(auth_client):
    """Verify that when enable_schema_checkpoints is True, checkpoint cards receive priority boost."""
    deck_id = await _deck(auth_client, "Hierarchy Deck", priority=50)
    note_leaf = await _note(auth_client, deck_id, "Leaf Card", "Leaf Detail")
    note_root = await _note(auth_client, deck_id, "Root Schema Card", "Foundational Schema")

    leaf_card_id = note_leaf["cards"][0]["id"]
    root_card_id = note_root["cards"][0]["id"]

    # Give leaf card a higher base priority (70 vs 40)
    await auth_client.patch(
        "/api/priority",
        json={"target": "card", "id": leaf_card_id, "priority": 70},
    )
    await auth_client.patch(
        "/api/priority",
        json={"target": "card", "id": root_card_id, "priority": 40},
    )

    # Mark root card as schema checkpoint
    await auth_client.patch(
        f"/api/cards/{root_card_id}/neuro-props",
        json={"is_schema_checkpoint": True},
    )

    # 1. With enable_schema_checkpoints = True (default):
    # Root schema card gets 40 + 100 = 140, which beats Leaf card's 70
    q_resp = await auth_client.get(f"/api/queue/session?deck={deck_id}&preview=10")
    assert q_resp.status_code == 200, q_resp.text
    queue_items = q_resp.json()["items"]
    assert len(queue_items) >= 2
    assert queue_items[0]["id"] == root_card_id
    assert queue_items[0]["is_schema_checkpoint"] is True

    # 2. Toggle enable_schema_checkpoints = False:
    # Checkpoint boost is 0, so Leaf card's 70 beats Root card's 40
    await auth_client.patch("/api/me", json={"enable_schema_checkpoints": False})

    q_resp_disabled = await auth_client.get(f"/api/queue/session?deck={deck_id}&preview=10")
    queue_items_disabled = q_resp_disabled.json()["items"]
    assert len(queue_items_disabled) >= 2
    assert queue_items_disabled[0]["id"] == leaf_card_id


@pytest.mark.asyncio
async def test_concept_graph_and_spreading_activation(auth_client):
    """Test creating concept edges and computing spreading activation."""
    deck_id = await _deck(auth_client, "Graph Deck")
    n1 = await _note(auth_client, deck_id, "Concept A", "Definition A")
    n2 = await _note(auth_client, deck_id, "Concept B", "Definition B")
    n3 = await _note(auth_client, deck_id, "Concept C", "Definition C")

    c1 = n1["cards"][0]["id"]
    c2 = n2["cards"][0]["id"]
    c3 = n3["cards"][0]["id"]

    # 1. Create edge C1 -> C2 with valid relationship_type
    edge_resp = await auth_client.post(
        "/api/graph/edges",
        json={
            "source_card_id": c1,
            "target_card_id": c2,
            "relationship_type": "prerequisite_of",
            "weight": 0.9,
        },
    )
    assert edge_resp.status_code == 201, edge_resp.text
    edge = edge_resp.json()
    assert edge["relationship_type"] == "prerequisite_of"
    assert edge["weight"] == 0.9

    # 2. Create edge C2 -> C3
    await auth_client.post(
        "/api/graph/edges",
        json={
            "source_card_id": c2,
            "target_card_id": c3,
            "relationship_type": "component_of",
            "weight": 0.8,
        },
    )

    # 3. Retrieve concept graph
    graph_resp = await auth_client.get("/api/graph")
    assert graph_resp.status_code == 200, graph_resp.text
    graph = graph_resp.json()
    assert len(graph["nodes"]) >= 3
    assert len(graph["edges"]) >= 2

    # 4. Compute Spreading Activation starting from C1
    related_resp = await auth_client.get(f"/api/graph/related/{c1}?max_hops=2&decay=0.6")
    assert related_resp.status_code == 200, related_resp.text
    related = related_resp.json()
    assert related["source_card_id"] == c1
    activated_ids = [node["card_id"] for node in related["activated_nodes"]]
    # Both C2 and C3 should receive spreading activation
    assert c2 in activated_ids
    assert c3 in activated_ids

    # 5. Delete an edge
    del_resp = await auth_client.delete(f"/api/graph/edges/{edge['id']}")
    assert del_resp.status_code == 204, del_resp.text


def _fake_neuro_llm(fail: bool = False):
    import json
    from app.services.grading_service import GradingUnavailable

    async def _mock_call(self, *args, **kwargs):
        if fail:
            raise GradingUnavailable("selected model failed")
        blob = (" ".join(str(a) for a in args) + " " + " ".join(str(v) for v in kwargs.values())).lower()
        if "variant_question" in blob:
            return json.dumps({"variant_question": "What fails if the pivot picks the minimum element?"})
        if "vignette" in blob:
            return json.dumps({"vignette": "A glowing silver powerhouse juggling lightning bolts of ATP."})
        if "is_accurate" in blob:
            return json.dumps({"is_accurate": False, "feedback": "HTTP 418 means I'm a teapot, not a server timeout."})
        if "discriminative_challenge" in blob:
            return json.dumps(
                {
                    "discriminative_challenge": "Which algorithm guarantees O(N log N) in the worst case?",
                    "key_distinction": "MergeSort guarantees O(N log N) worst case; QuickSort can degrade to O(N^2).",
                    "divergent_conditions": [
                        {"condition": "Sorted input with naive pivot", "choice_a": "O(N^2)", "choice_b": "O(N log N)"}
                    ],
                }
            )
        return "{}"

    return _mock_call


@pytest.mark.asyncio
async def test_prompt_mutation_endpoint(auth_client, monkeypatch):
    """Test generating a variant prompt for memory reconsolidation."""
    from app.services.grading_service import GradingService

    monkeypatch.setattr(GradingService, "_call_ollama", _fake_neuro_llm())
    deck_id = await _deck(auth_client, "Mutation Deck")
    note = await _note(auth_client, deck_id, "What is QuickSort time complexity?", "Average O(N log N)")
    card_id = note["cards"][0]["id"]

    mutate_resp = await auth_client.post(
        f"/api/review/{card_id}/mutate-prompt",
        json={"mutation_type": "counterfactual"},
    )
    assert mutate_resp.status_code == 200, mutate_resp.text
    res = mutate_resp.json()
    assert res["card_id"] == card_id
    assert res["mutation_type"] == "counterfactual"
    assert len(res["mutated_prompt"]) > 0


@pytest.mark.asyncio
async def test_mnemonic_synthesis_endpoint(auth_client, monkeypatch):
    """Test synthesizing a multi-sensory bizarre mnemonic vignette."""
    from app.services.grading_service import GradingService

    monkeypatch.setattr(GradingService, "_call_ollama", _fake_neuro_llm())
    deck_id = await _deck(auth_client, "Mnemonic Deck")
    note = await _note(auth_client, deck_id, "Mitochondria", "Powerhouse of the cell generating ATP")
    card_id = note["cards"][0]["id"]

    mnemonic_resp = await auth_client.post(f"/api/review/{card_id}/generate-mnemonic")
    assert mnemonic_resp.status_code == 200, mnemonic_resp.text
    res = mnemonic_resp.json()
    assert res["card_id"] == card_id
    assert len(res["mnemonic_vignette"]) > 0


@pytest.mark.asyncio
async def test_pretest_prediction_endpoint(auth_client, monkeypatch):
    """Test evaluating a pre-test prediction hypothesis and calculating RPE feedback."""
    from app.services.grading_service import GradingService

    monkeypatch.setattr(GradingService, "_call_ollama", _fake_neuro_llm())
    deck_id = await _deck(auth_client, "Prediction Deck")
    note = await _note(auth_client, deck_id, "What does HTTP 418 signify?", "I'm a teapot")
    card_id = note["cards"][0]["id"]

    pred_resp = await auth_client.post(
        f"/api/review/{card_id}/predict",
        json={
            "prediction": "It is a server timeout error",
            "confidence": 4,
        },
    )
    assert pred_resp.status_code == 200, pred_resp.text
    res = pred_resp.json()
    assert res["card_id"] == card_id
    assert res["confidence"] == 4
    # The user was highly confident (4) but predicted timeout instead of teapot -> prediction error detected
    assert res["high_confidence_error"] is True
    assert len(res["feedback"]) > 0


@pytest.mark.asyncio
async def test_contrast_drill_endpoint(auth_client, monkeypatch):
    """Test generating a Dentate Gyrus pattern separation contrast drill for sister pairs."""
    from app.services.grading_service import GradingService

    monkeypatch.setattr(GradingService, "_call_ollama", _fake_neuro_llm())
    deck_id = await _deck(auth_client, "Algorithms Contrast Deck")
    await _note(
        auth_client,
        deck_id,
        "What is the average time complexity of QuickSort algorithm?",
        "QuickSort averages O(N log N) with randomized pivot selection.",
    )
    await _note(
        auth_client,
        deck_id,
        "What is the average time complexity of MergeSort algorithm?",
        "MergeSort averages O(N log N) with divide and conquer partitioning.",
    )

    # Trigger interference scan
    scan_resp = await auth_client.post("/api/interference/scan")
    assert scan_resp.status_code == 200, scan_resp.text

    pairs_resp = await auth_client.get("/api/interference")
    assert pairs_resp.status_code == 200, pairs_resp.text
    pairs = pairs_resp.json()

    if pairs:
        pair_id = pairs[0]["id"]
        drill_resp = await auth_client.post(f"/api/interference/{pair_id}/contrast-drill")
        assert drill_resp.status_code == 200, drill_resp.text
        drill = drill_resp.json()
        assert drill["pair_id"] == pair_id
        assert len(drill["discriminative_challenge"]) > 0
        assert len(drill["key_distinction"]) > 0


@pytest.mark.asyncio
async def test_neuroscience_endpoints_raise_503_on_llm_failure(auth_client, monkeypatch):
    """All neuroscience endpoints must fail with HTTP 503 instead of returning heuristic fallbacks."""
    from app.services.grading_service import GradingService

    monkeypatch.setattr(GradingService, "_call_ollama", _fake_neuro_llm(fail=True))
    deck_id = await _deck(auth_client, "Strict Failure Deck")
    n1 = await _note(auth_client, deck_id, "QuickSort complexity?", "Average O(N log N)")
    await _note(auth_client, deck_id, "MergeSort complexity?", "Always O(N log N)")
    card_id = n1["cards"][0]["id"]

    await auth_client.post("/api/interference/scan")
    pairs = (await auth_client.get("/api/interference")).json()
    assert pairs, "expected sister pair for contrast drill failure test"

    for method_call in (
        auth_client.post(f"/api/review/{card_id}/mutate-prompt", json={"mutation_type": "counterfactual"}),
        auth_client.post(f"/api/review/{card_id}/generate-mnemonic"),
        auth_client.post(f"/api/review/{card_id}/predict", json={"prediction": "timeout", "confidence": 4}),
        auth_client.post(f"/api/interference/{pairs[0]['id']}/contrast-drill"),
    ):
        resp = await method_call
        assert resp.status_code == 503, resp.text


