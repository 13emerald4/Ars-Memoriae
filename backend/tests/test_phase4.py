"""Phase 4: sister-card interference detection and image occlusion."""

from __future__ import annotations

import io

import pytest

from app.services.interference_service import classify, find_candidates, similarity
from app.services.queue_service import ComposedItem, space_sisters
from app.services.rendering import occlusion_payload, render, shapes_of, slots_for

# ── similarity & classification ─────────────────────────────────────────────


class TestSimilarity:
    def test_identical_text_scores_one(self):
        assert similarity("to speak", "to speak") == pytest.approx(1.0, abs=0.01)

    def test_unrelated_text_scores_low(self):
        assert similarity("capital of France", "photosynthesis equation") < 0.2

    def test_morphological_variants_score_high(self):
        # Token overlap alone scores this 0.0; the adaptive weighting leans on
        # trigrams for short strings, which is the only reason it's caught.
        assert similarity("hablar", "hablarse") > 0.52

    def test_short_strings_lean_on_trigrams_long_ones_on_tokens(self):
        # Same token-overlap ratio, very different trigram overlap: the short
        # pair must not be judged purely on its (empty) token intersection.
        assert similarity("hablar", "comer") == 0.0
        assert similarity("hablar", "hablarse") > 0.5

    def test_word_order_does_not_matter(self):
        assert similarity("the cat sat", "sat the cat") > 0.8

    def test_stopwords_do_not_create_false_matches(self):
        assert similarity("what is the of a", "when is the of an") < 0.5

    def test_very_short_strings_are_skipped(self):
        assert similarity("a", "a") == 0.0


class TestClassification:
    """The distinction that makes this useful: similar fronts with *different*
    backs is the confusable case; similar on both sides is a duplicate."""

    def test_similar_front_different_back_is_interference(self):
        assert classify(0.9, 0.1) == "interference"

    def test_similar_on_both_sides_is_a_duplicate(self):
        assert classify(0.95, 0.95) == "duplicate"

    def test_different_front_similar_back_is_convergent(self):
        assert classify(0.1, 0.9) == "convergent"

    def test_unrelated_pairs_are_not_flagged(self):
        assert classify(0.2, 0.2) is None


# ── detection over a collection ─────────────────────────────────────────────


def test_finds_confusable_pairs_and_ignores_unrelated_ones():
    import uuid

    ids = [uuid.uuid4() for _ in range(5)]
    items = [
        (ids[0], "hablar", "to speak"),
        (ids[1], "hablar con", "to speak with someone"),   # confusable with [0]
        (ids[2], "comer", "to eat"),                        # unrelated
        (ids[3], "What is the capital of Australia?", "Canberra"),
        (ids[4], "What is the capital of Austria?", "Vienna"),  # classic interference
    ]
    found = find_candidates(items)
    pairs = {frozenset((c.note_a, c.note_b)): c for c in found}

    austria = pairs.get(frozenset((ids[3], ids[4])))
    assert austria is not None, "Australia/Austria should be flagged"
    assert austria.kind == "interference"
    assert austria.front_similarity > austria.back_similarity

    assert frozenset((ids[0], ids[2])) not in pairs
    assert frozenset((ids[1], ids[2])) not in pairs


def test_exact_duplicates_are_classified_as_duplicates():
    import uuid

    a, b = uuid.uuid4(), uuid.uuid4()
    found = find_candidates([(a, "Capital of France?", "Paris"), (b, "Capital of France?", "Paris")])
    assert len(found) == 1
    assert found[0].kind == "duplicate"


def test_interference_is_ranked_above_duplicates():
    import uuid

    ids = [uuid.uuid4() for _ in range(4)]
    found = find_candidates([
        (ids[0], "Capital of France?", "Paris"),
        (ids[1], "Capital of France?", "Paris"),          # duplicate
        (ids[2], "Spanish for to speak", "hablar"),
        (ids[3], "Spanish for to talk", "conversar"),      # interference
    ])
    assert found[0].kind == "interference"


def test_blocking_keeps_a_large_collection_tractable():
    """Every note sharing a boilerplate token must not become a candidate pair."""
    import uuid

    items = [(uuid.uuid4(), f"Question about topic {i}", f"Answer {i}") for i in range(300)]
    found = find_candidates(items)
    # "question"/"about"/"topic"/"answer" appear in all 300 and are blocked as
    # boilerplate, so we get far fewer than the ~45k unblocked pairs.
    assert len(found) < 300


def test_empty_and_single_collections_are_safe():
    import uuid

    assert find_candidates([]) == []
    assert find_candidates([(uuid.uuid4(), "solo", "card")]) == []


# ── queue spacing ───────────────────────────────────────────────────────────


def _item(note_id: str, cid: str) -> ComposedItem:
    return ComposedItem(
        kind="card", id=cid, deck_or_source_id="d", priority=50,
        effective_priority=50, note_id=note_id,
    )


class TestSpacing:
    def test_confusable_cards_are_pushed_apart(self):
        import uuid

        a, b = uuid.uuid4(), uuid.uuid4()
        others = [uuid.uuid4() for _ in range(4)]
        items = [_item(str(a), "1"), _item(str(b), "2")] + [
            _item(str(o), f"o{i}") for i, o in enumerate(others)
        ]
        spaced = space_sisters(items, {a: {b}, b: {a}}, min_gap=3)

        order = [i.note_id for i in spaced]
        assert abs(order.index(str(a)) - order.index(str(b))) >= 2
        assert len(spaced) == len(items)

    def test_sisters_ranked_last_are_still_pushed_apart(self):
        """Greedy placement used to append the last sister right after the
        other when both came last — the source of a flaky session test."""
        import uuid

        a, b = uuid.uuid4(), uuid.uuid4()
        fillers = [_item(str(uuid.uuid4()), f"o{i}") for i in range(4)]
        items = [*fillers, _item(str(a), "1"), _item(str(b), "2")]
        spaced = space_sisters(items, {a: {b}, b: {a}}, min_gap=3)

        order = [i.note_id for i in spaced]
        assert abs(order.index(str(a)) - order.index(str(b))) >= 2
        assert {i.id for i in spaced} == {i.id for i in items}

    def test_nothing_is_dropped_when_everything_conflicts(self):
        import uuid

        ids = [uuid.uuid4() for _ in range(4)]
        conflicts = {i: set(ids) - {i} for i in ids}
        items = [_item(str(i), str(n)) for n, i in enumerate(ids)]
        spaced = space_sisters(items, conflicts)
        assert len(spaced) == 4
        assert {i.id for i in spaced} == {i.id for i in items}

    def test_no_conflicts_leaves_order_untouched(self):
        items = [_item(f"n{i}", str(i)) for i in range(5)]
        assert space_sisters(items, {}) == items


# ── end-to-end interference ─────────────────────────────────────────────────


async def _note(client, deck_id, front, back):
    resp = await client.post(
        "/api/notes",
        json={"deck_id": deck_id, "template_kind": "basic",
              "field_values": {"Front": front, "Back": back}},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_scan_surfaces_pairs_and_dismissal_survives_a_rescan(auth_client):
    deck_id = (await auth_client.post("/api/decks", json={"name": "Geo"})).json()["id"]
    await _note(auth_client, deck_id, "What is the capital of Australia?", "Canberra")
    await _note(auth_client, deck_id, "What is the capital of Austria?", "Vienna")
    await _note(auth_client, deck_id, "Chemical symbol for gold", "Au")

    scan = (await auth_client.post("/api/interference/scan")).json()
    assert scan["notes_scanned"] == 3
    assert scan["pairs_found"] >= 1

    pairs = (await auth_client.get("/api/interference")).json()
    assert len(pairs) >= 1
    pair = pairs[0]
    assert pair["kind"] == "interference"
    assert {pair["back_a"], pair["back_b"]} == {"Canberra", "Vienna"}

    dismissed = (await auth_client.post(f"/api/interference/{pair['id']}/dismiss")).json()
    assert dismissed["status"] == "dismissed"
    assert (await auth_client.get("/api/interference")).json() == []

    # A rescan must not resurrect what the user already judged (§ dismissals).
    await auth_client.post("/api/interference/scan")
    assert (await auth_client.get("/api/interference")).json() == []
    assert len((await auth_client.get("/api/interference?include_dismissed=true")).json()) >= 1


async def test_queue_keeps_confusable_cards_apart(auth_client):
    deck_id = (await auth_client.post("/api/decks", json={"name": "Spacing"})).json()["id"]
    await _note(auth_client, deck_id, "What is the capital of Australia?", "Canberra")
    await _note(auth_client, deck_id, "What is the capital of Austria?", "Vienna")
    fillers = [
        ("Who wrote Hamlet?", "Shakespeare"),
        ("Boiling point of water", "100 degrees Celsius"),
        ("Chemical symbol for gold", "Au"),
        ("Largest planet", "Jupiter"),
    ]
    for front, back in fillers:
        await _note(auth_client, deck_id, front, back)

    await auth_client.patch("/api/me", json={"daily_new_limit": 50, "queue_time_budget_minutes": 60})
    await auth_client.post("/api/interference/scan")

    items = (await auth_client.get("/api/queue/session")).json()["items"]
    fronts = [i["front"] for i in items]
    assert len(fronts) == 6, "spacing must reorder, never drop"

    aus = fronts.index("What is the capital of Australia?")
    aut = fronts.index("What is the capital of Austria?")
    assert abs(aus - aut) >= 2, f"confusable cards ended up adjacent: {fronts}"


# ── image occlusion ─────────────────────────────────────────────────────────

SHAPES = [
    {"id": "o1", "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.1, "label": "Frontal lobe"},
    {"id": "o2", "x": 0.5, "y": 0.4, "w": 0.2, "h": 0.15, "label": "Occipital lobe"},
]
IO_FIELDS = {
    "Image": "/media/u/brain.png",
    "Shapes": SHAPES,
    "Header": "Lobes of the brain",
    "Back Extra": "Gross anatomy",
}


class TestOcclusionRendering:
    def test_one_card_per_region(self):
        assert slots_for("image_occlusion", IO_FIELDS) == ["o1", "o2"]

    def test_malformed_shapes_are_dropped_not_crashed(self):
        fields = {"Shapes": [{"x": 0.1}, {"x": 0, "y": 0, "w": 0, "h": 0.1}, "junk", SHAPES[0]]}
        assert [s["id"] for s in shapes_of(fields)] == ["o1"]

    def test_coordinates_are_clamped_into_the_image(self):
        shapes = shapes_of({"Shapes": [{"id": "o1", "x": -3, "y": 0.5, "w": 9, "h": 0.2}]})
        assert shapes[0]["x"] == 0.0
        assert shapes[0]["w"] == 1.0

    def test_text_rendering_names_the_region_and_its_label(self):
        front, back = render("image_occlusion", IO_FIELDS, "o2")
        assert "Lobes of the brain" in front
        assert "o2" in front
        assert back.startswith("Occipital lobe")
        assert "Gross anatomy" in back

    def test_unlabelled_region_says_so_rather_than_rendering_blank(self):
        fields = {**IO_FIELDS, "Shapes": [{"id": "o1", "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.1}]}
        _, back = render("image_occlusion", fields, "o1")
        assert "reveal only" in back

    def test_payload_carries_every_shape_plus_the_target(self):
        payload = occlusion_payload(IO_FIELDS, "o2")
        assert payload["image"] == "/media/u/brain.png"
        assert payload["target"] == "o2"
        assert len(payload["shapes"]) == 2, "all masks are needed, not just the target"

    def test_no_payload_without_an_image(self):
        assert occlusion_payload({"Shapes": SHAPES}, "o1") is None

    def test_imported_note_without_parsable_masks_still_renders(self):
        """Anki occlusion notes arrive with captions but no shapes we can read."""
        front, back = render("image_occlusion", {"Header": "Heart", "Back Extra": "Ch. 4"}, "o1")
        assert front == "Heart"
        assert back == "Ch. 4"


PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


async def test_upload_image_then_build_an_occlusion_note(auth_client):
    upload = await auth_client.post(
        "/api/media", files={"file": ("brain.png", io.BytesIO(PNG), "image/png")}
    )
    assert upload.status_code == 201, upload.text
    url = upload.json()["url"]
    assert url.startswith("/media/")
    assert upload.json()["kind"] == "image"

    deck_id = (await auth_client.post("/api/decks", json={"name": "Anatomy"})).json()["id"]
    note_type = (
        await auth_client.post(
            "/api/note-types",
            json={"name": "Occlusion", "template_kind": "image_occlusion",
                  "fields": {"fields": ["Image", "Shapes", "Header", "Back Extra"]}},
        )
    ).json()

    note = await auth_client.post(
        "/api/notes",
        json={"deck_id": deck_id, "note_type_id": note_type["id"],
              "field_values": {**IO_FIELDS, "Image": url}},
    )
    assert note.status_code == 201, note.text
    cards = note.json()["cards"]
    assert sorted(c["template_slot"] for c in cards) == ["o1", "o2"]

    o1 = next(c for c in cards if c["template_slot"] == "o1")
    assert o1["occlusion"]["target"] == "o1"
    assert o1["occlusion"]["image"] == url
    assert len(o1["occlusion"]["shapes"]) == 2


async def test_occlusion_cards_flow_through_the_queue(auth_client):
    upload = await auth_client.post(
        "/api/media", files={"file": ("d.png", io.BytesIO(PNG), "image/png")}
    )
    url = upload.json()["url"]
    deck_id = (await auth_client.post("/api/decks", json={"name": "IOQueue"})).json()["id"]
    nt = (
        await auth_client.post(
            "/api/note-types", json={"name": "IO2", "template_kind": "image_occlusion", "fields": {}}
        )
    ).json()
    await auth_client.post(
        "/api/notes",
        json={"deck_id": deck_id, "note_type_id": nt["id"],
              "field_values": {**IO_FIELDS, "Image": url}},
    )
    await auth_client.patch("/api/me", json={"daily_new_limit": 50})

    item = (await auth_client.get("/api/queue/next")).json()
    assert item["template_kind"] == "image_occlusion"
    assert item["occlusion"] is not None
    assert item["occlusion"]["target"] in ("o1", "o2")
    assert item["note_id"]

    # And it schedules like any other card.
    confirm = await auth_client.post(
        f"/api/review/{item['id']}/confirm", json={"final_grade": "good", "overridden": False}
    )
    assert confirm.status_code == 200
    assert confirm.json()["state"] == "learning"


async def test_editing_shapes_adds_and_retires_cards(auth_client):
    deck_id = (await auth_client.post("/api/decks", json={"name": "Edit IO"})).json()["id"]
    nt = (
        await auth_client.post(
            "/api/note-types", json={"name": "IO3", "template_kind": "image_occlusion", "fields": {}}
        )
    ).json()
    note = (
        await auth_client.post(
            "/api/notes",
            json={"deck_id": deck_id, "note_type_id": nt["id"], "field_values": IO_FIELDS},
        )
    ).json()

    updated = await auth_client.patch(
        f"/api/notes/{note['id']}",
        json={"field_values": {**IO_FIELDS, "Shapes": [
            SHAPES[0],
            {"id": "o3", "x": 0.7, "y": 0.7, "w": 0.1, "h": 0.1, "label": "Cerebellum"},
        ]}},
    )
    assert updated.status_code == 200, updated.text
    cards = {c["template_slot"]: c for c in updated.json()["cards"]}
    assert set(cards) == {"o1", "o2", "o3"}
    # o2's region is gone, but its history is kept — suspended, not deleted.
    assert cards["o2"]["suspended"] is True
    assert cards["o3"]["suspended"] is False


async def test_upload_rejects_unsupported_types(auth_client):
    resp = await auth_client.post(
        "/api/media", files={"file": ("evil.exe", io.BytesIO(b"MZ..."), "application/x-msdownload")}
    )
    assert resp.status_code == 415


async def test_upload_filename_cannot_escape_the_media_directory(auth_client):
    resp = await auth_client.post(
        "/api/media",
        files={"file": ("../../../etc/passwd.png", io.BytesIO(PNG), "image/png")},
    )
    assert resp.status_code == 201
    url = resp.json()["url"]
    assert ".." not in url
    assert url.count("/") == 3  # /media/<user_id>/<random>.png
