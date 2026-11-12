import pytest
from httpx import AsyncClient

from app.services.question_format_service import (
    extract_question_code_from_starter,
    format_question_with_code_blocks,
)


def test_format_extracts_starter_types_and_stub_without_harness():
    front = (
        "Using the LA02 data definitions, implement `countItems(inventory: Inventory): number`."
    )
    starter = (
        'type Item = { kind: "weapon"; name: string } | { kind: "empty" };\n'
        "type Inventory = Item[];\n\n"
        "function countItems(inventory: Inventory): number {\n"
        "  // TODO\n"
        "  return -1;\n"
        "}\n\n"
        "// ---- Sandbox harness (not part of the exam) ----\n"
        "function runAll() { return []; }\n"
    )
    formatted = format_question_with_code_blocks(front, starter_code=starter, language="typescript")
    assert "```ts\n" in formatted
    assert "type Inventory = Item[];" in formatted
    assert "function countItems(inventory: Inventory): number" in formatted
    assert "Sandbox harness" not in formatted
    # Idempotency check
    assert (
        format_question_with_code_blocks(formatted, starter_code=starter, language="typescript")
        == formatted
    )


def test_format_preserves_existing_fences_and_repairs_closing_tag():
    sample = (
        "**Task 1.1:** Complete `getGenreFrequency`:\n"
        "```ts\n"
        "public getGenreFrequency(genre: Genre): number {\n"
        "  return -1;\n"
        "}\n"
        "```\n\n"
        "Tests provided."
    )
    assert format_question_with_code_blocks(sample, language="typescript") == sample


def test_format_standalone_unfenced_code_and_preserves_non_code_prose():
    humanities = (
        "Who built the aqueduct of Segovia and during which Roman emperor's reign was it completed?"
    )
    assert format_question_with_code_blocks(humanities) == humanities

    standalone_code = (
        "What does this Python function return?\n\n"
        "def mystery(xs: list[int]) -> list[int]:\n"
        "    return [x * 2 for x in xs if x > 0]\n\n"
        "Explain the filter and transform steps."
    )
    formatted = format_question_with_code_blocks(standalone_code, language="python")
    assert "```python\ndef mystery(xs: list[int]) -> list[int]:" in formatted
    assert "    return [x * 2 for x in xs if x > 0]\n```" in formatted


def test_extract_class_spec_skeleton_from_front():
    front = (
        "Implement encapsulated class `HeartRateMonitor`:\n"
        "- Private fields: `private readonly windowMs: number; private readings: Reading[];`\n"
        "- `constructor(windowMinutes: number)`: throws when <= 0.\n"
        "- `record(atMs: number, bpm: number): void`: appends reading.\n"
    )
    starter = 'export type Reading = { atMs: number; bpm: number };\nexport function runHeartRateMonitor() {}\n'
    lang, snippet = extract_question_code_from_starter(front, starter, "typescript")
    assert lang == "ts"
    assert "export type Reading" in snippet
    assert "class HeartRateMonitor" in snippet
    assert "private readonly windowMs: number;" in snippet
    assert "public record(atMs: number, bpm: number): void" in snippet
    assert "runHeartRateMonitor" not in snippet


@pytest.mark.asyncio
async def test_import_and_note_endpoints_format_code_questions_going_forward(auth_client: AsyncClient):
    deck_resp = await auth_client.post("/api/decks", json={"name": "Going Forward Code Format"})
    assert deck_resp.status_code == 201
    deck_id = deck_resp.json()["id"]

    # 1. JSON import with code card whose front omitted code fences
    imp_resp = await auth_client.post(
        "/api/import/json",
        json={
            "deck": "Going Forward Code Format",
            "notes": [
                {
                    "kind": "code",
                    "front": "Implement `doubleAll(nums: number[]): number[]`.",
                    "back": "function doubleAll(nums: number[]): number[] { return nums.map(n => n * 2); }",
                    "starter_code": "function doubleAll(nums: number[]): number[] {\n  // TODO\n  return [];\n}",
                }
            ],
        },
    )
    assert imp_resp.status_code == 201, imp_resp.text

    # 2. Direct POST /api/notes with starter_code and unfenced Front
    note_resp = await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {
                "Front": "Implement `square(n: number): number`.",
                "Back": "function square(n: number): number { return n * n; }",
                "starter_code": "function square(n: number): number {\n  // TODO\n  return 0;\n}",
                "language": "typescript",
            },
        },
    )
    assert note_resp.status_code == 201, note_resp.text
    note = note_resp.json()
    assert "```ts\nfunction square(n: number): number" in note["field_values"]["Front"]

    # 3. Verify imported card also received fenced code block in Queue
    q_resp = await auth_client.get(f"/api/queue/session?deck={deck_id}")
    assert q_resp.status_code == 200
    fronts = [item["front"] for item in q_resp.json()["items"]]
    assert any("```ts\nfunction doubleAll(nums: number[]): number[]" in f for f in fronts)
    assert any("```ts\nfunction square(n: number): number" in f for f in fronts)
