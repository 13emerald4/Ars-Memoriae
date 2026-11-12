import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_deck_and_card_documentation(auth_client: AsyncClient):
    # 1. Create deck with thematic nature, documentation, and source documents
    deck_resp = await auth_client.post(
        "/api/decks",
        json={
            "name": "Distributed Systems",
            "thematic_nature": "Consensus Protocols & Fault Tolerance",
            "documentation": "Covers Paxos, Raft, and Viewstamped Replication for high-availability clusters.",
            "source_documents": [
                {"title": "In Search of an Understandable Consensus Algorithm (Ongaro, Ousterhout)", "type": "paper"},
                {"title": "Paxos Made Simple (Lamport)", "type": "paper"},
            ],
        },
    )
    assert deck_resp.status_code == 201, deck_resp.text
    deck = deck_resp.json()
    assert deck["thematic_nature"] == "Consensus Protocols & Fault Tolerance"
    assert "Covers Paxos, Raft" in deck["documentation"]
    assert len(deck["source_documents"]) == 2
    deck_id = deck["id"]

    # 2. Check list_decks returns the documentation fields
    list_resp = await auth_client.get("/api/decks")
    assert list_resp.status_code == 200
    found = next((d for d in list_resp.json() if d["id"] == deck_id), None)
    assert found is not None
    assert found["thematic_nature"] == "Consensus Protocols & Fault Tolerance"
    assert len(found["source_documents"]) == 2

    # 3. Create a card in this deck (without explicit card documentation)
    # It should automatically inherit the deck's theme, documentation, and source documents
    note_resp = await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {
                "Front": "What is the primary role of the leader in Raft?",
                "Back": "To manage log replication and maintain strong consistency across follower nodes.",
            },
        },
    )
    assert note_resp.status_code == 201, note_resp.text
    note = note_resp.json()
    assert len(note["cards"]) >= 1
    card = note["cards"][0]
    assert card["thematic_nature"] == "Consensus Protocols & Fault Tolerance"
    assert "Covers Paxos, Raft" in card["documentation"]
    assert len(card["source_documents"]) == 2

    # 4. Create another card with card-specific documentation override
    note_override_resp = await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {
                "Front": "What is split brain in Paxos?",
                "Back": "When network partitioning causes multiple leaders to accept conflicting writes.",
            },
            "thematic_nature": "Network Partitions & Safety",
            "documentation": "Specifically addresses CAP theorem network split failure modes.",
            "source_documents": [{"title": "Brewer's Conjecture & CAP Theorem"}],
        },
    )
    assert note_override_resp.status_code == 201
    card2 = note_override_resp.json()["cards"][0]
    assert card2["thematic_nature"] == "Network Partitions & Safety"
    assert "specifically addresses cap" in card2["documentation"].lower()
    assert len(card2["source_documents"]) == 1

    # 5. Verify queue item has deck and card documentation attached
    session_resp = await auth_client.get(f"/api/queue/session?deck={deck_id}")
    assert session_resp.status_code == 200, session_resp.text
    items = session_resp.json()["items"]
    assert len(items) >= 2
    item1 = next((i for i in items if i["id"] == card["id"]), None)
    assert item1 is not None
    assert item1["deck_thematic_nature"] == "Consensus Protocols & Fault Tolerance"
    assert item1["card_thematic_nature"] == "Consensus Protocols & Fault Tolerance"
    assert len(item1["deck_source_documents"]) == 2

    # 6. Verify PATCH deck updates documentation
    patch_deck_resp = await auth_client.patch(
        f"/api/decks/{deck_id}",
        json={"thematic_nature": "Modern Distributed Consensus & Byzantine Fault Tolerance"},
    )
    assert patch_deck_resp.status_code == 200
    assert patch_deck_resp.json()["thematic_nature"] == "Modern Distributed Consensus & Byzantine Fault Tolerance"

    # 7. Test show_thematic_context toggle in user profile
    me_resp = await auth_client.get("/api/me")
    assert me_resp.json()["show_thematic_context"] is True

    patch_me = await auth_client.patch("/api/me", json={"show_thematic_context": False})
    assert patch_me.status_code == 200
    assert patch_me.json()["show_thematic_context"] is False


@pytest.mark.asyncio
async def test_deck_document_upload_list_and_delete(auth_client: AsyncClient):
    # 1. Create a deck
    deck_resp = await auth_client.post(
        "/api/decks",
        json={"name": "CPSC 210 Software Construction", "thematic_nature": "Design Patterns"},
    )
    assert deck_resp.status_code == 201
    deck_id = deck_resp.json()["id"]

    # 2. Upload a markdown documentation file
    doc_content = (
        b"# CPSC 210 Specification\n\n"
        b"## Result Types\n"
        b"The Result type represents either a successful outcome with a value or a failure with an error message.\n"
        b"Always use assertOk to unwrap the value in unit tests.\n\n"
        b"## Invariants\n"
        b"All mutations must preserve the class invariant.\n"
    )

    upload_resp = await auth_client.post(
        f"/api/decks/{deck_id}/documents",
        files={"file": ("cpsc210_spec.md", doc_content, "text/markdown")},
        data={"title": "CPSC 210 Course Specifications"},
    )
    assert upload_resp.status_code == 201, upload_resp.text
    doc_data = upload_resp.json()
    assert doc_data["title"] == "CPSC 210 Course Specifications"
    assert doc_data["filename"] == "cpsc210_spec.md"
    assert doc_data["segment_count"] >= 1
    assert len(doc_data["locators"]) >= 1
    doc_id = doc_data["id"]

    # 3. List documents for deck
    list_resp = await auth_client.get(f"/api/decks/{deck_id}/documents")
    assert list_resp.status_code == 200
    docs = list_resp.json()["documents"]
    assert len(docs) == 1
    assert docs[0]["id"] == doc_id
    assert docs[0]["title"] == "CPSC 210 Course Specifications"

    # 4. Delete document
    del_resp = await auth_client.delete(f"/api/decks/{deck_id}/documents/{doc_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"

    # Verify list is now empty
    list_resp2 = await auth_client.get(f"/api/decks/{deck_id}/documents")
    assert list_resp2.status_code == 200
    assert len(list_resp2.json()["documents"]) == 0


@pytest.mark.asyncio
async def test_deck_document_query_grounding(auth_client: AsyncClient, monkeypatch):
    from app.services.grading_service import GradingService

    # 1. Create deck and upload doc
    deck_resp = await auth_client.post(
        "/api/decks",
        json={"name": "Algorithmic Invariants"},
    )
    assert deck_resp.status_code == 201
    deck_id = deck_resp.json()["id"]

    doc_content = (
        b"# Heaps and Priority Queues\n\n"
        b"## Min-Heap Property\n"
        b"In a min-heap, for any given node C, if P is a parent node of C, then the key of P is less than or equal to the key of C.\n"
        b"The root node contains the minimum element in the entire heap.\n"
    )

    upload_resp = await auth_client.post(
        f"/api/decks/{deck_id}/documents",
        files={"file": ("heap_spec.md", doc_content, "text/markdown")},
        data={"title": "Heap Specifications"},
    )
    assert upload_resp.status_code == 201

    async def fake_generate(self, prompt, model=None, schema=None, **kwargs):
        return (
            "**→ Found in Docs.** [Heap Specifications · Min-Heap Property]: In a min-heap, "
            "the key of the parent node P is less than or equal to the key of child C.\n\n"
            "**→ Explanation.** The code maintains the heap invariant by bubbling up smaller elements to the root.\n\n"
            "**→ Key Takeaway.** Root always holds the minimal element."
        )

    async def fake_verify(self):
        return ["qwen2.5-coder:7b", "qwen2.5-coder:3b"]

    monkeypatch.setattr(GradingService, "_generate", fake_generate)
    monkeypatch.setattr(GradingService, "verify_engine", fake_verify)

    # 2. Query deck documents endpoint
    query_resp = await auth_client.post(
        f"/api/decks/{deck_id}/query-docs",
        json={
            "query": "parent.val <= child.val",
            "full_code": "function heapifyUp() { if (parent.val > child.val) swap(); }",
            "language": "typescript",
        },
    )
    assert query_resp.status_code == 200, query_resp.text
    q_data = query_resp.json()
    assert "Heap Specifications" in (q_data.get("doc_citation") or "") or "Heap Specifications" in q_data["found_info"]
    assert q_data["doc_citation"] is not None
    assert "heap invariant" in (q_data["explanation"] or "").lower()
    assert len(q_data["citations"]) >= 1

    # 3. Test explain-selection endpoint with mode="docs" and deck_id
    explain_resp = await auth_client.post(
        "/api/code/explain-selection",
        json={
            "selected_code": "if (parent.val > child.val) swap();",
            "language": "typescript",
            "mode": "docs",
            "deck_id": deck_id,
        },
    )
    assert explain_resp.status_code == 200, explain_resp.text
    e_data = explain_resp.json()
    assert "Cited Document" in e_data["explanation"] or "Found in Docs" in e_data["explanation"]
    assert e_data["doc_citation"] is not None
    assert e_data.get("verbatim_passage") is not None
    assert len(e_data["doc_matches"]) >= 1


@pytest.mark.asyncio
async def test_subdeck_inherits_parent_deck_documents(auth_client: AsyncClient, monkeypatch):
    from app.services.grading_service import GradingService

    # 1. Create parent deck (e.g. CPSC 210)
    parent_resp = await auth_client.post(
        "/api/decks",
        json={"name": "CPSC 210"},
    )
    assert parent_resp.status_code == 201
    parent_id = parent_resp.json()["id"]

    # 2. Upload document to parent deck
    doc_content = (
        b"# Solutions Manual\n\n"
        b"## Grade Calculation\n"
        b"LA01 Card 4: gradeFromPoints(points, total) converts points/total to a percentage, "
        b"then to a letter grade with thresholds: 80 A, 68 B, 55 C, 50 D, else F.\n"
    )
    upload_resp = await auth_client.post(
        f"/api/decks/{parent_id}/documents",
        files={"file": ("solutions_manual.md", doc_content, "text/markdown")},
        data={"title": "Solutions Manual"},
    )
    assert upload_resp.status_code == 201

    # 3. Create subdeck (e.g. LA01) with parent_id set to parent_id
    subdeck_resp = await auth_client.post(
        "/api/decks",
        json={"name": "LA01", "parent_id": parent_id},
    )
    assert subdeck_resp.status_code == 201
    subdeck_id = subdeck_resp.json()["id"]

    async def fake_generate(self, prompt, model=None, schema=None, **kwargs):
        return (
            "**→ Cited Document.** [Solutions Manual · Grade Calculation]\n"
            "**→ Verbatim Specification.**\n"
            "> LA01 Card 4: gradeFromPoints(points, total) converts points/total to a percentage, "
            "then to a letter grade with thresholds: 80 A, 68 B, 55 C, 50 D, else F.\n"
            "**→ Relevant Rules.** Convert points/total to percentage, division last, then map to letter.\n"
            "**→ Key Takeaway.** Letter thresholds: 80 A, 68 B, 55 C, 50 D, else F."
        )

    monkeypatch.setattr(GradingService, "_generate", fake_generate)

    # 4. Search docs specifying subdeck_id (which has no direct docs attached)
    explain_resp = await auth_client.post(
        "/api/code/explain-selection",
        json={
            "selected_code": "function gradeFromPoints(points: number, total: number)",
            "language": "typescript",
            "mode": "docs",
            "deck_id": subdeck_id,
        },
    )
    assert explain_resp.status_code == 200, explain_resp.text
    data = explain_resp.json()
    assert "Cited Document" in data["explanation"]
    assert "Solutions Manual" in data["explanation"]
    assert data["verbatim_passage"] is not None
    assert "gradeFromPoints" in data["verbatim_passage"]
    assert len(data["doc_matches"]) >= 1
    assert data["doc_matches"][0]["source_title"] == "Solutions Manual"
    assert "LA01 Card 4" in data["doc_matches"][0]["content"]

    # 5. Ask a follow-up question via /api/code/ask-docs
    async def fake_qa_generate(self, prompt, model=None, schema=None, **kwargs):
        assert "Prior Discussion" in prompt or "Student Question" in prompt
        assert "Why is 80 checked before 68?" in prompt
        return "Checking 80 first ensures higher grade thresholds are evaluated before lower ones."

    monkeypatch.setattr(GradingService, "_generate", fake_qa_generate)

    qa_resp = await auth_client.post(
        "/api/code/ask-docs",
        json={
            "question": "Why is 80 checked before 68?",
            "selected_code": "if (pct >= 80) return 'A';",
            "full_code": "function gradeFromPoints(points, total) { const pct = points / total * 100; if (pct >= 80) return 'A'; }",
            "deck_id": subdeck_id,
            "history": [
                {"role": "user", "content": "What are the grade thresholds?"},
                {"role": "assistant", "content": "80 is A, 68 is B, 55 is C, 50 is D, else F."},
            ],
        },
    )
    assert qa_resp.status_code == 200, qa_resp.text
    qa_data = qa_resp.json()
    assert "Checking 80 first" in qa_data["answer"]
    assert qa_data["doc_citation"] is not None
    assert "Solutions Manual" in qa_data["doc_citation"]
    assert len(qa_data["citations"]) >= 1

    # Empty question validation
    bad_resp = await auth_client.post("/api/code/ask-docs", json={"question": "   "})
    assert bad_resp.status_code == 400

    # 6. Ask question without any attached deck documents (verifying pre-training fallback)
    async def fake_qa_generate_nodocs(self, prompt, model=None, schema=None, **kwargs):
        assert "Synthesize BOTH the attached course documentation and your general pre-trained programming knowledge" in prompt
        assert "No attached course documentation extracts found" in prompt
        assert "What does account.balance >= 0 check?" in prompt
        return "It checks that the balance is non-negative before proceeding with the operation."

    monkeypatch.setattr(GradingService, "_generate", fake_qa_generate_nodocs)

    nodocs_resp = await auth_client.post(
        "/api/code/ask-docs",
        json={
            "question": "What does account.balance >= 0 check?",
            "selected_code": "if (!(account.balance >= 0)) throw new Error('Account balance must be >= 0');",
            "language": "typescript",
        },
    )
    assert nodocs_resp.status_code == 200, nodocs_resp.text
    nodocs_data = nodocs_resp.json()
    assert "non-negative" in nodocs_data["answer"]
    assert nodocs_data["doc_citation"] is None
    assert len(nodocs_data["citations"]) == 0


@pytest.mark.asyncio
async def test_ask_docs_card_context_and_stable_prefix(auth_client: AsyncClient, monkeypatch):
    from app.services.grading_service import GradingService

    deck_resp = await auth_client.post("/api/decks", json={"name": "Algorithms Lab"})
    assert deck_resp.status_code == 201
    deck_id = deck_resp.json()["id"]

    card_front = "Write clamp(val, lo, hi) returning val bounded cleanly to [lo, hi]."
    card_back = "```typescript\nfunction clamp(val: number, lo: number, hi: number): number {\n  return Math.max(lo, Math.min(val, hi));\n}\n```"
    starter_tests = "test('bounds', () => { assertEquals(clamp(-1, 0, 10), 0); });"

    note_resp = await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {
                "Front": card_front,
                "Back": card_back,
                "starter_tests": starter_tests,
            },
        },
    )
    assert note_resp.status_code == 201, note_resp.text
    card_id = note_resp.json()["cards"][0]["id"]

    captured_prompts: list[str] = []

    async def fake_generate(self, prompt, model=None, schema=None, **kwargs):
        captured_prompts.append(prompt)
        return "Check how lower and upper bounds interact when val is out of range."

    monkeypatch.setattr(GradingService, "_generate", fake_generate)

    first_resp = await auth_client.post(
        "/api/code/ask-docs",
        json={
            "question": "Why does my upper bound fail?",
            "selected_code": "if (val > hi) return lo;",
            "full_code": "function clamp(val: number, lo: number, hi: number) { if (val > hi) return lo; return val; }",
            "language": "typescript",
            "deck_id": deck_id,
            "card_id": card_id,
            "user_code": "function clamp(val: number, lo: number, hi: number) { if (val > hi) return lo; return val; }",
            "user_test_code": "test('upper', () => { assertEquals(clamp(12, 0, 10), 10); });",
            "execution_summary": "Status: Wrong Answer (0/1 tests passed); Error: Expected 10, got 0",
            "revealed": False,
        },
    )
    assert first_resp.status_code == 200, first_resp.text

    second_resp = await auth_client.post(
        "/api/code/ask-docs",
        json={
            "question": "Now explain why Math.max/Math.min is equivalent.",
            "selected_code": "return Math.max(lo, Math.min(val, hi));",
            "full_code": "return Math.max(lo, Math.min(val, hi));",
            "language": "typescript",
            "deck_id": deck_id,
            "card_id": card_id,
            "user_code": "function clamp(val: number, lo: number, hi: number) { return Math.max(lo, Math.min(val, hi)); }",
            "user_test_code": starter_tests,
            "execution_summary": "Status: Accepted (1/1 tests passed)",
            "revealed": True,
            "history": [
                {"role": "user", "content": "Why does my upper bound fail?"},
                {"role": "assistant", "content": "Check your return value when val exceeds hi."},
            ],
        },
    )
    assert second_resp.status_code == 200, second_resp.text
    assert len(captured_prompts) == 2

    p1, p2 = captured_prompts
    # Entire card question, solution, starter tests, and work in progress must be present
    assert card_front in p1
    assert "Math.max(lo, Math.min(val, hi))" in p1
    assert starter_tests in p1
    assert "if (val > hi) return lo;" in p1
    assert "Expected 10, got 0" in p1
    assert "assertEquals(clamp(12, 0, 10), 10)" in p1

    # Prefix-cache order: immutable card context -> mutable student work -> question
    idx_front = p1.index(card_front)
    idx_back = p1.index("Math.max(lo, Math.min(val, hi))")
    idx_exec = p1.index("Expected 10, got 0")
    idx_q = p1.index("Why does my upper bound fail?")
    assert idx_front < idx_back < idx_exec < idx_q

    # Static instructions + card question/solution prefix is byte-identical across turns
    anchor = "Math.max(lo, Math.min(val, hi))"
    prefix_end_1 = p1.index(anchor) + len(anchor)
    prefix_end_2 = p2.index(anchor) + len(anchor)
    assert p1[:prefix_end_1] == p2[:prefix_end_2]
    assert "Status: Accepted (1/1 tests passed)" in p2



