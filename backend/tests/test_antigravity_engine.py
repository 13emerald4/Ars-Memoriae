"""Tests for Antigravity subscription CLI (`agy -p`) integration across all LLM consumers."""

from __future__ import annotations

import asyncio
import io
import json

import pytest

from app.core.config import settings
from app.schemas.core import UserUpdate
from app.schemas.review import SocraticLineHintRequest, SocraticRequest, SubmitAnswerRequest
from app.services.grading_service import (
    SCORE_SCHEMA,
    GradingService,
    GradingUnavailable,
    _to_standard_json_schema,
    is_allowed_grading_model,
    is_allowed_qwen_coder_model,
    is_antigravity_model,
    model_provider,
    resolve_model,
    strip_antigravity_prefix,
)


class _FakeSubprocess:
    def __init__(self, stdout: str, stderr: str = "", returncode: int = 0) -> None:
        self._stdout = stdout.encode("utf-8")
        self._stderr = stderr.encode("utf-8")
        self.returncode = returncode
        self.killed = False

    async def communicate(self):
        return self._stdout, self._stderr

    def kill(self):
        self.killed = True
        self.returncode = -9


def test_antigravity_model_allowlist_and_schema_conversion():
    assert is_antigravity_model("antigravity:gemini-3.8-flash-medium") is True
    assert is_antigravity_model("ANTIGRAVITY:Claude-Sonnet-4-6") is True
    assert is_antigravity_model("antigravity:gpt-oss-120b-medium") is True
    assert is_antigravity_model("antigravity:bogus-model") is False
    assert is_antigravity_model("qwen2.5-coder:7b") is False

    # Existing Ollama-specific predicate must stay strict for local discovery.
    assert is_allowed_qwen_coder_model("antigravity:gemini-3.8-flash-medium") is False
    assert is_allowed_grading_model("antigravity:gemini-3.8-flash-medium") is True
    assert is_allowed_grading_model("qwen2.5-coder:7b") is True

    assert strip_antigravity_prefix("ANTIGRAVITY:Gemini-3.8-Flash-Low") == "gemini-3.8-flash-low"
    assert model_provider("antigravity:gemini-3.8-flash-low") == "antigravity"
    assert model_provider("qwen2.5-coder:3b") == "ollama"

    # Fail-closed default: resolve_model ignores Antigravity unless allow_antigravity=True.
    assert resolve_model("antigravity:gemini-3.8-flash-medium") == settings.default_grading_model
    assert (
        resolve_model("antigravity:gemini-3.8-flash-medium", allow_antigravity=True)
        == "antigravity:gemini-3.8-flash-medium"
    )

    lowered = _to_standard_json_schema(SCORE_SCHEMA)
    assert lowered["type"] == "object"
    assert lowered["properties"]["score"]["type"] == "number"
    assert lowered["properties"]["matched_points"]["type"] == "array"
    assert lowered["properties"]["matched_points"]["items"]["type"] == "string"

    # Pydantic validators permit Antigravity models and still reject unknown ones.
    assert UserUpdate(grading_model="antigravity:gemini-3.8-flash-low").grading_model == "antigravity:gemini-3.8-flash-low"
    assert SubmitAnswerRequest(typed_answer="x", latency_ms=100, model="antigravity:claude-sonnet-4-6").model == "antigravity:claude-sonnet-4-6"
    assert SocraticRequest(model="antigravity:gemini-3.8-flash-medium").model == "antigravity:gemini-3.8-flash-medium"
    assert SocraticLineHintRequest(code="x", line_number=1, model="antigravity:gemini-3.8-flash-high").model == "antigravity:gemini-3.8-flash-high"

    with pytest.raises(ValueError):
        UserUpdate(grading_model="antigravity:unknown-provider")


@pytest.mark.asyncio
async def test_generate_antigravity_invokes_agy_with_schema_and_uses_structured_output(monkeypatch):
    seen_cmds: list[tuple[str, ...]] = []

    monkeypatch.setattr("app.services.grading_service.resolve_antigravity_executable", lambda: "agy")

    async def fake_exec(*cmd, **kwargs):
        seen_cmds.append(cmd)
        envelope = {
            "status": "SUCCESS",
            "response": "Wrapped commentary that should be ignored when structured_output exists",
            "structured_output": {
                "score": 92,
                "confidence": 0.95,
                "matched_points": ["Correct invariant"],
                "missed_points": [],
                "overlooked_phrases": [],
                "weaknesses": [],
                "improvements": [],
                "persistent_weaknesses": [],
                "reasoning": "Exact and concise.",
            },
        }
        return _FakeSubprocess(json.dumps(envelope))

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    # Unauthorized/default GradingService fails closed even if passed an Antigravity model string.
    blocked_svc = GradingService(model="antigravity:gemini-3.8-flash-medium")
    assert blocked_svc.allow_antigravity is False
    assert blocked_svc.model == settings.default_grading_model
    assert model_provider(blocked_svc.model) == "ollama"

    ollama_fallback_models: list[str] = []

    async def fake_blocked_ollama(prompt, model, schema=None, **kwargs):
        ollama_fallback_models.append(model)
        return "{}"

    monkeypatch.setattr(blocked_svc, "_generate_ollama", fake_blocked_ollama)
    await blocked_svc._generate("hello", model="antigravity:gemini-3.8-flash-medium")
    assert ollama_fallback_models == [settings.default_grading_model]
    assert seen_cmds == []
    with pytest.raises(GradingUnavailable):
        await blocked_svc._generate_antigravity("hello", model="antigravity:gemini-3.8-flash-medium")

    svc = GradingService(model="antigravity:gemini-3.8-flash-medium", allow_antigravity=True)
    result = await svc.grade_with_escalation(
        front="Implement add(a, b)",
        back="return a + b",
        user_answer="return a + b",
        profile="math_code",
        force_escalate=True,
    )

    # Critical: even on ALWAYS_ESCALATE profiles (`math_code`) or `force_escalate`,
    # Antigravity never drops down to local Ollama `qwen2.5-coder:7b`.
    assert len(seen_cmds) == 1
    cmd = seen_cmds[0]
    assert "--model" in cmd and cmd[cmd.index("--model") + 1] == "gemini-3.8-flash-medium"
    assert "--json-schema" in cmd
    schema_arg = json.loads(cmd[cmd.index("--json-schema") + 1])
    assert schema_arg["type"] == "object"
    assert "--disable-slash-commands" in cmd

    assert result["score"] == 92
    assert result["grade"] == "easy"
    assert result["model_used"] == "antigravity:gemini-3.8-flash-medium"
    assert result["escalated"] is False


@pytest.mark.asyncio
async def test_generate_antigravity_surfaces_signin_error(monkeypatch):
    monkeypatch.setattr("app.services.grading_service.resolve_antigravity_executable", lambda: "agy")

    async def fake_exec(*cmd, **kwargs):
        envelope = {"status": "ERROR", "error": "Authentication required: run agy to sign in"}
        return _FakeSubprocess(json.dumps(envelope), returncode=1)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    svc = GradingService(model="antigravity:gemini-3.8-flash-low", allow_antigravity=True)
    with pytest.raises(GradingUnavailable) as exc:
        await svc._generate("hello", model="antigravity:gemini-3.8-flash-low")
    assert "sign in" in str(exc.value).lower() or "sign-in" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_leech_remediation_uses_antigravity_model(monkeypatch):
    called_models: list[str] = []

    async def fake_agy(self, prompt, model, schema=None, **kwargs):
        called_models.append(model)
        if '"hint"' in prompt:
            return json.dumps({"hint": "Check loop boundary condition."})
        return json.dumps({"kind": "split", "rationale": "Split concepts", "cards": [{"front": "A", "back": "B"}]})

    monkeypatch.setattr(GradingService, "_generate_antigravity", fake_agy)
    svc = GradingService(model="antigravity:claude-sonnet-4-6", allow_antigravity=True)
    out = await svc.suggest_leech_remediation("Q", "A", 4, ["wrong"])
    hint = await svc.generate_weakness_hint("Q", "A", ["off-by-one"])
    assert out["kind"] == "split"
    assert hint["hint"] == "Check loop boundary condition."
    assert called_models == ["antigravity:claude-sonnet-4-6", "antigravity:claude-sonnet-4-6"]


@pytest.mark.asyncio
async def test_all_ai_endpoints_route_to_antigravity_subscription(auth_client, monkeypatch):
    agy_calls: list[tuple[str, bool]] = []

    async def fake_verify_all(self):
        return {
            "ollama": {"connected": False, "base_url": self.base_url, "models": [], "error": "offline"},
            "antigravity": {
                "connected": True,
                "installed": True,
                "cli_path": "agy",
                "models": ["antigravity:gemini-3.8-flash-medium", "antigravity:claude-sonnet-4-6"],
                "catalog": [],
                "error": None,
            },
        }

    async def fake_agy(self, prompt, model, schema=None, **kwargs):
        agy_calls.append((model, schema is not None))
        p_low = prompt.lower()
        if "variant_question" in p_low:
            return json.dumps({"variant_question": "Mutated invariant check?"})
        if "vignette" in p_low:
            return json.dumps({"vignette": "A glowing crystal balanced on a giant silver scale."})
        if "is_accurate" in p_low:
            return json.dumps({"is_accurate": True, "feedback": "Aligned with the core invariant."})
        if "discriminative_challenge" in p_low:
            return json.dumps(
                {
                    "discriminative_challenge": "What distinguishes Concept A from B?",
                    "key_distinction": "A operates synchronously; B yields.",
                    "divergent_conditions": [{"condition": "Blocking call", "choice_a": "Blocks", "choice_b": "Suspends"}],
                }
            )
        if "rule of atomicity" in p_low or "atomic flashcards" in p_low:
            return json.dumps({"cards": [{"front": "Q1", "back": "A1"}, {"front": "Q2", "back": "A2"}]})
        if '"hint"' in p_low and "target_concept" in p_low:
            return json.dumps({"hint": "Check loop boundary", "target_concept": "Bounds"})
        if '"hint"' in p_low:
            return json.dumps({"hint": "Recall the base case first."})
        if '"message"' in p_low and '"on_track"' in p_low:
            return json.dumps({"message": "What invariant must hold on entry?", "on_track": True})
        if '"lesson"' in p_low and '"key_points"' in p_low:
            return json.dumps({"lesson": "Debt minimization follows balance sheet stress.", "key_points": ["Pay debt"]})
        if '"definition"' in p_low and '"related_terms"' in p_low:
            return json.dumps(
                {
                    "definition": "A binary search tree stores keys in sorted symmetric order.",
                    "context_explanation": "Enables logarithmic search.",
                    "example": "bst.find(42)",
                    "domain": "Data Structures",
                    "related_terms": ["AVL", "Invariant"],
                }
            )
        if '"slug"' in p_low and '"starter_codes"' in p_low:
            return json.dumps(
                {
                    "title": "Binary Tree Depth",
                    "slug": "binary-tree-depth-ag",
                    "difficulty": "Easy",
                    "category": "Trees",
                    "description": "Compute maximum depth.",
                    "examples": [],
                    "constraints": [],
                    "starter_codes": {"python": "def depth(root):\n    pass\n"},
                    "test_cases": [],
                }
            )
        if '"cards"' in p_low:
            return json.dumps(
                {
                    "cards": [
                        {
                            "kind": "qa",
                            "front": "What replaces profit maximization?",
                            "back": "Debt minimization.",
                            "quote": "shifts from profit maximization to debt minimization",
                        }
                    ]
                }
            )
        if '"score"' in p_low:
            return json.dumps(
                {
                    "score": 88,
                    "confidence": 0.9,
                    "matched_points": ["debt minimization"],
                    "missed_points": [],
                    "overlooked_phrases": [],
                    "weaknesses": [],
                    "improvements": [],
                    "persistent_weaknesses": [],
                    "reasoning": "Accurate summary.",
                }
            )
        return "**→ Cited Document.** [Spec · S1]\n\n**→ Meaning & Application.** Applies Antigravity reasoning.\n\n**→ Key Takeaway.** Clear invariant."

    monkeypatch.setattr(GradingService, "verify_all_engines", fake_verify_all)
    monkeypatch.setattr(GradingService, "_generate_antigravity", fake_agy)

    # Default test user is NOT allowlisted until their email is configured in antigravity_allowed_emails.
    me_before = (await auth_client.get("/api/me")).json()
    assert me_before["can_use_antigravity"] is False

    # Authorize this owner account for Antigravity subscription access.
    monkeypatch.setattr(settings, "antigravity_allowed_emails", me_before["email"])
    me_after = (await auth_client.get("/api/me")).json()
    assert me_after["can_use_antigravity"] is True

    # Switch user to Antigravity subscription model + grant consent.
    patch_resp = await auth_client.patch(
        "/api/me",
        json={"llm_grading_consent": True, "grading_model": "antigravity:gemini-3.8-flash-medium"},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    assert patch_resp.json()["grading_model"] == "antigravity:gemini-3.8-flash-medium"

    # 1. /api/models, /api/llm/status, /api/llm/vram
    models_resp = await auth_client.get("/api/models")
    assert models_resp.status_code == 200
    assert "antigravity:gemini-3.8-flash-medium" in models_resp.json()["models"]

    status_resp = await auth_client.get("/api/llm/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["provider"] == "antigravity"
    assert status_resp.json()["connected"] is True
    assert status_resp.json()["model_ready"] is True
    assert status_resp.json()["vram"] is None

    vram_resp = await auth_client.get("/api/llm/vram?model=antigravity:gemini-3.8-flash-medium")
    assert vram_resp.status_code == 200
    assert vram_resp.json()["gpu_name"] == "Antigravity Subscription (Cloud)"

    # Create cited source + deck + cards (covers document generation, extract generation, lessons, review).
    doc_md = "# Balance Sheet\n\n## Section One\n\nDuring distress the private sector shifts from profit maximization to debt minimization.\n"
    doc = (
        await auth_client.post(
            "/api/documents",
            files={"file": ("macro.md", io.BytesIO(doc_md.encode()), "text/markdown")},
        )
    ).json()
    src_id = doc["source_id"]
    extracts = (await auth_client.get(f"/api/sources/{src_id}/extracts")).json()
    ext_id = extracts[0]["id"]

    gen_src = await auth_client.post(f"/api/extracts/{ext_id}/generate-cards", json={"max_cards": 1})
    assert gen_src.status_code == 200, gen_src.text
    assert len(gen_src.json()["suggestions"]) == 1

    gen_doc = await auth_client.post(f"/api/documents/{src_id}/generate-deck", json={"max_cards_per_section": 1})
    assert gen_doc.status_code == 200, gen_doc.text
    assert len(gen_doc.json()["cards"]) >= 1

    accepted = (
        await auth_client.post(
            f"/api/documents/{src_id}/accept-deck",
            json={
                "deck": "Antigravity Deck",
                "cards": [
                    {
                        "kind": "qa",
                        "front": "What replaces profit maximization?",
                        "back": "Debt minimization.",
                        "quote": "shifts from profit maximization to debt minimization",
                        "quote_verified": True,
                        "locator": extracts[0]["locator"],
                        "extract_id": ext_id,
                    }
                ],
            },
        )
    ).json()
    deck_id = accepted["deck_id"]
    cards = (await auth_client.get(f"/api/cards?deck_id={deck_id}")).json()
    card_id = cards[0]["id"]

    # Attach source doc to deck so deck doc queries run against it too.
    await auth_client.post(
        f"/api/decks/{deck_id}/documents",
        files={"file": ("Spec.md", io.BytesIO(b"# Spec\nSection 2: Debt minimization rule."), "text/markdown")},
    )

    # Add a similar sister card + scan for interference contrast drill.
    await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {
                "Front": "What replaces profit maximization in a balance sheet recession?",
                "Back": "Debt minimization and balance sheet repair.",
            },
        },
    )
    await auth_client.post("/api/interference/scan")
    pairs = (await auth_client.get("/api/interference")).json()

    # Review grading, socratic guide, line hint, lesson
    ans = await auth_client.post(
        f"/api/review/{card_id}/answer",
        json={"typed_answer": "debt minimization", "latency_ms": 1200},
    )
    assert ans.status_code == 200, ans.text
    assert ans.json()["model_used"] == "antigravity:gemini-3.8-flash-medium"
    assert ans.json()["score"] == 88

    guide = await auth_client.post(f"/api/review/{card_id}/guide", json={"history": [], "message": "hint"})
    assert guide.status_code == 200, guide.text
    assert guide.json()["model_used"] == "antigravity:gemini-3.8-flash-medium"

    line_hint = await auth_client.post(
        f"/api/review/{card_id}/line-hint",
        json={"code": "def f():\n    pass", "line_number": 2, "language": "python"},
    )
    assert line_hint.status_code == 200, line_hint.text
    assert line_hint.json()["degraded"] is False

    lesson = await auth_client.get(f"/api/review/{card_id}/lesson")
    assert lesson.status_code == 200, lesson.text
    assert lesson.json()["model_used"] == "antigravity:gemini-3.8-flash-medium"

    # Neuroscience endpoints (via _call_ollama bridge -> _generate_antigravity)
    mut = await auth_client.post(f"/api/review/{card_id}/mutate-prompt", json={"mutation_type": "counterfactual"})
    assert mut.status_code == 200, mut.text
    assert mut.json()["model_used"] == "antigravity:gemini-3.8-flash-medium"

    mnem = await auth_client.post(f"/api/review/{card_id}/generate-mnemonic")
    assert mnem.status_code == 200, mnem.text
    assert mnem.json()["model_used"] == "antigravity:gemini-3.8-flash-medium"

    pred = await auth_client.post(
        f"/api/review/{card_id}/predict",
        json={"prediction": "debt minimization", "confidence": 3},
    )
    assert pred.status_code == 200, pred.text
    assert pred.json()["is_accurate"] is True

    if pairs:
        drill = await auth_client.post(f"/api/interference/{pairs[0]['id']}/contrast-drill")
        assert drill.status_code == 200, drill.text
        assert "synchronously" in drill.json()["key_distinction"]

    # Memory Athlete decomposition
    decomp = await auth_client.post(
        "/api/memory/decompose",
        json={"front": "Complex Q", "back": "Long answer"},
    )
    assert decomp.status_code == 200, decomp.text
    assert len(decomp.json()["cards"]) == 2

    # Lexicon lookup
    lex = await auth_client.post(
        "/api/lexicon/lookup",
        json={"term": "Binary Search Tree", "card_id": card_id, "deck_name": "Antigravity Deck"},
    )
    assert lex.status_code == 200, lex.text
    assert lex.json()["model_used"] == "antigravity:gemini-3.8-flash-medium"

    # Code Practice + Deck Docs QA
    forge = await auth_client.post(
        "/api/code/problems/forge",
        json={"topic": "Binary Tree Depth", "difficulty": "Easy", "target_language": "python"},
    )
    assert forge.status_code == 200, forge.text

    hint = await auth_client.post(
        f"/api/code/problems/{forge.json()['slug']}/socratic",
        json={"code": "def depth(root):\n    return 0", "language": "python", "hint_type": "conceptual"},
    )
    assert hint.status_code == 200, hint.text
    assert len(hint.json()["hint"]) > 0

    explain = await auth_client.post(
        "/api/code/explain-selection",
        json={"selected_code": "debt minimization", "mode": "docs", "deck_id": deck_id},
    )
    assert explain.status_code == 200, explain.text
    assert explain.json()["model_used"] == "antigravity:gemini-3.8-flash-medium"

    ask_docs = await auth_client.post(
        "/api/code/ask-docs",
        json={"question": "Why does it shift?", "deck_id": deck_id},
    )
    assert ask_docs.status_code == 200, ask_docs.text
    assert ask_docs.json()["model_used"] == "antigravity:gemini-3.8-flash-medium"

    q_docs = await auth_client.post(
        f"/api/decks/{deck_id}/query-docs",
        json={"query": "debt minimization"},
    )
    assert q_docs.status_code == 200, q_docs.text
    assert q_docs.json()["model_used"] == "antigravity:gemini-3.8-flash-medium"

    # Confirm all outbound generations went to the Antigravity model
    assert len(agy_calls) >= 14
    assert all(m == "antigravity:gemini-3.8-flash-medium" for m, _ in agy_calls)


@pytest.mark.asyncio
async def test_antigravity_restricted_to_owner_only(client, monkeypatch):
    """Only emails explicitly allowlisted in ANTIGRAVITY_ALLOWED_EMAILS can see, select, or run Antigravity."""
    import types
    import uuid

    from fastapi import HTTPException

    from app.services.code_ai_service import CodeAiService

    owner_email = f"owner-{uuid.uuid4().hex[:8]}@example.com"
    other_email = f"other-{uuid.uuid4().hex[:8]}@example.com"

    # Allowlist ONLY owner_email (case-insensitive normalization should preserve match).
    monkeypatch.setattr(settings, "antigravity_allowed_emails", f"  {owner_email.upper()} ")

    reg_owner = await client.post("/api/auth/register", json={"email": owner_email, "password": "hunter2hunter2"})
    assert reg_owner.status_code == 201, reg_owner.text
    owner_headers = {"Authorization": f"Bearer {reg_owner.json()['access_token']}"}

    reg_other = await client.post("/api/auth/register", json={"email": other_email, "password": "hunter2hunter2"})
    assert reg_other.status_code == 201, reg_other.text
    other_headers = {"Authorization": f"Bearer {reg_other.json()['access_token']}"}
    client.cookies.clear()

    agy_discovery_calls = 0
    agy_exec_calls: list[str] = []

    async def fake_verify_ollama(self):
        raise GradingUnavailable("offline")

    async def fake_discover_agy():
        nonlocal agy_discovery_calls
        agy_discovery_calls += 1
        return (["antigravity:gemini-3.8-flash-medium"], "C:\\fake\\agy.cmd", None)

    async def fake_agy_exec(self, prompt, model, schema=None, **kwargs):
        agy_exec_calls.append(model)
        raise AssertionError("Unauthorized user must never invoke Antigravity CLI subprocess!")

    monkeypatch.setattr(GradingService, "_verify_ollama", fake_verify_ollama)
    monkeypatch.setattr("app.services.grading_service.discover_antigravity_models", fake_discover_agy)
    monkeypatch.setattr(GradingService, "_generate_antigravity", fake_agy_exec)

    # 1. /api/me reflects capability flag per user.
    owner_me = (await client.get("/api/me", headers=owner_headers)).json()
    other_me = (await client.get("/api/me", headers=other_headers)).json()
    assert owner_me["can_use_antigravity"] is True
    assert other_me["can_use_antigravity"] is False

    # 2. Other user gets zero Antigravity discovery, models, catalog, or cli_path metadata leak.
    other_models = await client.get("/api/models", headers=other_headers)
    assert other_models.status_code == 200
    other_models_data = other_models.json()
    assert not any(m.startswith("antigravity:") for m in other_models_data["models"])
    assert other_models_data["providers"]["antigravity"]["authorized"] is False
    assert other_models_data["providers"]["antigravity"]["connected"] is False
    assert other_models_data["providers"]["antigravity"]["models"] == []
    assert other_models_data["providers"]["antigravity"].get("cli_path") is None
    assert other_models_data["providers"]["antigravity"].get("catalog", []) == []

    other_status = await client.get("/api/llm/status", headers=other_headers)
    assert other_status.status_code == 200
    assert other_status.json()["providers"]["antigravity"]["authorized"] is False
    assert other_status.json()["providers"]["antigravity"]["models"] == []
    assert other_status.json()["providers"]["antigravity"].get("cli_path") is None
    assert agy_discovery_calls == 0

    # 3. Owner DOES see Antigravity models and discovery runs only for owner.
    owner_models = await client.get("/api/models", headers=owner_headers)
    assert owner_models.status_code == 200
    assert "antigravity:gemini-3.8-flash-medium" in owner_models.json()["models"]
    assert owner_models.json()["providers"]["antigravity"]["authorized"] is True
    assert agy_discovery_calls == 1

    owner_patch = await client.patch(
        "/api/me",
        headers=owner_headers,
        json={"grading_model": "antigravity:gemini-3.8-flash-medium"},
    )
    assert owner_patch.status_code == 200

    # 4. Other user is rejected (403) when trying to query VRAM, save preference, or invoke any AI route with antigravity:*.
    vram_forbidden = await client.get(
        "/api/llm/vram?model=antigravity:gemini-3.8-flash-medium",
        headers=other_headers,
    )
    assert vram_forbidden.status_code == 403

    patch_forbidden = await client.patch(
        "/api/me",
        headers=other_headers,
        json={"grading_model": "antigravity:gemini-3.8-flash-medium"},
    )
    assert patch_forbidden.status_code == 403

    # Grant LLM consent for other user & scaffold deck/card/source so endpoint permission checks run post-auth.
    consent_resp = await client.patch(
        "/api/me",
        headers=other_headers,
        json={"llm_grading_consent": True},
    )
    assert consent_resp.status_code == 200

    deck_id = (
        await client.post("/api/decks", headers=other_headers, json={"name": "Other Deck"})
    ).json()["id"]
    await client.post(
        "/api/notes",
        headers=other_headers,
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {"Front": "Q", "Back": "A"},
        },
    )
    card_id = (await client.get(f"/api/cards?deck_id={deck_id}", headers=other_headers)).json()[0]["id"]
    src_id = (
        await client.post(
            "/api/documents",
            headers=other_headers,
            files={"file": ("doc.md", io.BytesIO(b"# Doc\n\n## Sec\n\nFact sentence."), "text/markdown")},
        )
    ).json()["source_id"]
    ext_id = (await client.get(f"/api/sources/{src_id}/extracts", headers=other_headers)).json()[0]["id"]

    blocked_requests = [
        client.post(
            f"/api/review/{card_id}/answer",
            headers=other_headers,
            json={"typed_answer": "A", "latency_ms": 500, "model": "antigravity:gemini-3.8-flash-medium"},
        ),
        client.post(
            f"/api/review/{card_id}/guide",
            headers=other_headers,
            json={"history": [], "message": "hint", "model": "antigravity:gemini-3.8-flash-medium"},
        ),
        client.post(
            f"/api/review/{card_id}/line-hint",
            headers=other_headers,
            json={"code": "x = 1", "line_number": 1, "language": "python", "model": "antigravity:gemini-3.8-flash-medium"},
        ),
        client.post(
            f"/api/extracts/{ext_id}/generate-cards",
            headers=other_headers,
            json={"max_cards": 1, "model": "antigravity:gemini-3.8-flash-medium"},
        ),
        client.post(
            f"/api/documents/{src_id}/generate-deck",
            headers=other_headers,
            json={"max_cards_per_section": 1, "model": "antigravity:gemini-3.8-flash-medium"},
        ),
        client.post(
            "/api/code/explain-selection",
            headers=other_headers,
            json={"selected_code": "x", "mode": "docs", "deck_id": deck_id, "model": "antigravity:gemini-3.8-flash-medium"},
        ),
        client.post(
            "/api/code/ask-docs",
            headers=other_headers,
            json={"question": "why?", "deck_id": deck_id, "model": "antigravity:gemini-3.8-flash-medium"},
        ),
        client.post(
            f"/api/decks/{deck_id}/query-docs",
            headers=other_headers,
            json={"query": "x", "model": "antigravity:gemini-3.8-flash-medium"},
        ),
    ]
    for coro in blocked_requests:
        resp = await coro
        assert resp.status_code == 403, f"Expected 403 for unauthorized user, got {resp.status_code}: {resp.text}"

    # 5. Stale DB value on an unauthorized user falls back to local Ollama (fail-closed) when no explicit model is sent,
    #    while explicit antigravity requests raise HTTP 403 in both GradingService.for_user and CodeAiService.for_user.
    stale_other = types.SimpleNamespace(
        email=other_email,
        grading_model="antigravity:gemini-3.8-flash-medium",
    )
    fallback_svc = GradingService.for_user(stale_other)
    assert fallback_svc.allow_antigravity is False
    assert model_provider(fallback_svc.model) == "ollama"
    assert fallback_svc.model == settings.default_grading_model

    fallback_code_svc = CodeAiService.for_user(stale_other)
    assert fallback_code_svc.grading_service.allow_antigravity is False
    assert model_provider(fallback_code_svc.grading_service.model) == "ollama"

    with pytest.raises(HTTPException) as exc_grade:
        GradingService.for_user(stale_other, requested_model="antigravity:gemini-3.8-flash-medium")
    assert exc_grade.value.status_code == 403

    with pytest.raises(HTTPException) as exc_code:
        CodeAiService.for_user(stale_other, requested_model="antigravity:gemini-3.8-flash-medium")
    assert exc_code.value.status_code == 403

    assert agy_exec_calls == []


@pytest.mark.asyncio
async def test_strict_model_no_fallback_and_cache_invalidation_on_model_switch(auth_client, monkeypatch):
    """Switching to antigravity:gemini-3.8-flash-low must bypass stale medium caches
    (GradingCache, CardLesson, LexiconCache) and return HTTP 503 with zero fallback
    to smaller or Ollama models across all AI endpoints when the selected model fails."""
    state = {"fail": False}
    seen_models: list[str] = []
    fail_models: list[str] = []
    ollama_calls: list[str] = []

    async def fake_verify_all(self):
        return {
            "ollama": {"connected": False, "base_url": self.base_url, "models": [], "error": "offline"},
            "antigravity": {
                "connected": True,
                "installed": True,
                "cli_path": "agy",
                "models": [
                    "antigravity:gemini-3.8-flash-low",
                    "antigravity:gemini-3.8-flash-medium",
                ],
                "catalog": [],
                "error": None,
            },
        }

    async def fail_if_ollama(self, *args, **kwargs):
        ollama_calls.append(str(kwargs.get("model") or self.model))
        raise AssertionError("Must never fall back to local Ollama when Antigravity is selected")

    async def fake_agy(self, prompt, model, schema=None, **kwargs):
        seen_models.append(model)
        if state["fail"]:
            fail_models.append(model)
            raise GradingUnavailable(f"{model} quota exhausted")

        p_low = prompt.lower()
        if '"slug"' in p_low and '"starter_codes"' in p_low:
            return json.dumps(
                {
                    "title": "Quorum State",
                    "slug": "quorum-state-strict",
                    "difficulty": "Easy",
                    "category": "Distributed",
                    "description": "Compute quorum intersection.",
                    "examples": [],
                    "constraints": [],
                    "starter_codes": {"python": "def quorum(n):\n    return n // 2 + 1\n"},
                    "test_cases": [],
                }
            )
        if '"lesson"' in p_low and '"key_points"' in p_low:
            return json.dumps(
                {
                    "lesson": f"Lesson from {model}: balance sheet repair drives deleveraging.",
                    "key_points": [f"Point from {model}"],
                }
            )
        if '"definition"' in p_low and '"related_terms"' in p_low:
            return json.dumps(
                {
                    "definition": f"Definition by {model}: bounded quorum lease.",
                    "context_explanation": "Ensures linearizability.",
                    "example": "lease.renew()",
                    "domain": "Distributed Systems",
                    "related_terms": ["Paxos"],
                }
            )
        if '"score"' in p_low:
            if "wrong attempt" in p_low:
                return json.dumps(
                    {
                        "score": 45,
                        "confidence": 0.9,
                        "matched_points": [],
                        "missed_points": ["Balance sheet repair drives deleveraging."],
                        "overlooked_phrases": [],
                        "weaknesses": ["off-by-one boundary"],
                        "improvements": [],
                        "persistent_weaknesses": [],
                        "reasoning": "Missed core mechanism.",
                    }
                )
            score_val = 74 if model == "antigravity:gemini-3.8-flash-low" else 88
            return json.dumps(
                {
                    "score": score_val,
                    "confidence": 0.9,
                    "matched_points": ["deleveraging"],
                    "missed_points": [],
                    "overlooked_phrases": [],
                    "weaknesses": [],
                    "improvements": [],
                    "persistent_weaknesses": [],
                    "reasoning": f"Graded strictly by {model}.",
                }
            )
        return json.dumps(
            {
                "cards": [
                    {
                        "kind": "qa",
                        "front": "What replaces profit maximization in distress?",
                        "back": "Debt minimization.",
                        "quote": "Balance sheet repair drives deleveraging during corporate distress.",
                    }
                ]
            }
        )

    monkeypatch.setattr(GradingService, "verify_all_engines", fake_verify_all)
    monkeypatch.setattr(GradingService, "_generate_antigravity", fake_agy)
    monkeypatch.setattr(GradingService, "_generate_ollama", fail_if_ollama)

    me = (await auth_client.get("/api/me")).json()
    monkeypatch.setattr(settings, "antigravity_allowed_emails", me["email"])

    patch_med = await auth_client.patch(
        "/api/me",
        json={"llm_grading_consent": True, "grading_model": "antigravity:gemini-3.8-flash-medium"},
    )
    assert patch_med.status_code == 200, patch_med.text

    # Setup document, extract, 2 cited cards (sister pair), deck document, weakness state, forged code problem.
    doc_md = "# Balance Sheet\n\n## Sec One\n\nBalance sheet repair drives deleveraging during corporate distress.\n"
    src_id = (
        await auth_client.post(
            "/api/documents",
            files={"file": ("strict.md", io.BytesIO(doc_md.encode()), "text/markdown")},
        )
    ).json()["source_id"]
    extracts = (await auth_client.get(f"/api/sources/{src_id}/extracts")).json()
    ext_id = extracts[0]["id"]
    loc = extracts[0]["locator"]

    accepted = (
        await auth_client.post(
            f"/api/documents/{src_id}/accept-deck",
            json={
                "deck": "Strict Model Deck",
                "cards": [
                    {
                        "kind": "qa",
                        "front": "What drives deleveraging during corporate distress?",
                        "back": "Balance sheet repair.",
                        "quote": "Balance sheet repair drives deleveraging during corporate distress.",
                        "quote_verified": True,
                        "locator": loc,
                        "extract_id": ext_id,
                    },
                    {
                        "kind": "qa",
                        "front": "What drives deleveraging during private corporate distress?",
                        "back": "Balance sheet repair and debt minimization.",
                        "quote": "Balance sheet repair drives deleveraging during corporate distress.",
                        "quote_verified": True,
                        "locator": loc,
                        "extract_id": ext_id,
                    },
                ],
            },
        )
    ).json()
    deck_id = accepted["deck_id"]
    cards = (await auth_client.get(f"/api/cards?deck_id={deck_id}")).json()
    card1_id, card2_id = cards[0]["id"], cards[1]["id"]

    await auth_client.post(
        f"/api/decks/{deck_id}/documents",
        files={"file": ("Spec.md", io.BytesIO(b"# Spec\nDeleveraging invariant."), "text/markdown")},
    )
    await auth_client.post("/api/interference/scan")
    pairs = (await auth_client.get("/api/interference")).json()
    assert pairs, "Expected sister pair for contrast drill coverage"
    pair_id = pairs[0]["id"]

    forge = await auth_client.post(
        "/api/code/problems/forge",
        json={"topic": "Quorum State", "difficulty": "Easy", "target_language": "python"},
    )
    assert forge.status_code == 200, forge.text
    slug = forge.json()["slug"]

    # Record active weakness on card1 via a failed answer + confirm.
    bad_ans = await auth_client.post(
        f"/api/review/{card1_id}/answer",
        json={"typed_answer": "wrong attempt", "latency_ms": 500},
    )
    assert bad_ans.status_code == 200, bad_ans.text
    confirm_bad = await auth_client.post(
        f"/api/review/{card1_id}/confirm",
        json={"final_grade": "hard", "overridden": True, "typed_answer": "wrong attempt", "latency_ms": 500},
    )
    assert confirm_bad.status_code == 200, confirm_bad.text

    # Populate medium caches for grading, lesson, and lexicon.
    med_ans = await auth_client.post(
        f"/api/review/{card1_id}/answer",
        json={"typed_answer": "deleveraging", "latency_ms": 800},
    )
    assert med_ans.status_code == 200 and med_ans.json()["score"] == 88
    assert med_ans.json()["cached"] is False

    med_lesson = await auth_client.get(f"/api/review/{card1_id}/lesson")
    assert med_lesson.status_code == 200 and med_lesson.json()["model_used"] == "antigravity:gemini-3.8-flash-medium"
    assert med_lesson.json()["cached"] is False

    med_lex = await auth_client.post(
        "/api/lexicon/lookup",
        json={"term": "Ephemeral Quorum Lease", "card_id": card1_id, "deck_name": "Strict Model Deck"},
    )
    assert med_lex.status_code == 200 and med_lex.json()["model_used"] == "antigravity:gemini-3.8-flash-medium"
    assert med_lex.json()["cached"] is False

    # Switch user to antigravity:gemini-3.8-flash-low.
    patch_low = await auth_client.patch(
        "/api/me",
        json={"grading_model": "antigravity:gemini-3.8-flash-low"},
    )
    assert patch_low.status_code == 200, patch_low.text
    assert patch_low.json()["grading_model"] == "antigravity:gemini-3.8-flash-low"

    seen_models.clear()

    # 1) Cache bypass verification on model switch: medium caches MUST NOT be replayed under low.
    low_ans = await auth_client.post(
        f"/api/review/{card1_id}/answer",
        json={"typed_answer": "deleveraging", "latency_ms": 700},
    )
    assert low_ans.status_code == 200, low_ans.text
    assert low_ans.json()["cached"] is False
    assert low_ans.json()["model_used"] == "antigravity:gemini-3.8-flash-low"
    assert low_ans.json()["score"] == 74

    low_ans_cached = await auth_client.post(
        f"/api/review/{card1_id}/answer",
        json={"typed_answer": "deleveraging", "latency_ms": 700},
    )
    assert low_ans_cached.json()["cached"] is True and low_ans_cached.json()["score"] == 74

    low_lesson = await auth_client.get(f"/api/review/{card1_id}/lesson")
    assert low_lesson.status_code == 200, low_lesson.text
    assert low_lesson.json()["cached"] is False
    assert low_lesson.json()["model_used"] == "antigravity:gemini-3.8-flash-low"
    assert "antigravity:gemini-3.8-flash-low" in low_lesson.json()["body"]

    low_lesson_cached = await auth_client.get(f"/api/review/{card1_id}/lesson")
    assert low_lesson_cached.json()["cached"] is True

    low_lex = await auth_client.post(
        "/api/lexicon/lookup",
        json={"term": "Ephemeral Quorum Lease", "card_id": card1_id, "deck_name": "Strict Model Deck"},
    )
    assert low_lex.status_code == 200, low_lex.text
    assert low_lex.json()["cached"] is False
    assert low_lex.json()["model_used"] == "antigravity:gemini-3.8-flash-low"

    low_lex_cached = await auth_client.post(
        "/api/lexicon/lookup",
        json={"term": "Ephemeral Quorum Lease", "card_id": card1_id, "deck_name": "Strict Model Deck"},
    )
    assert low_lex_cached.json()["cached"] is True

    assert seen_models == [
        "antigravity:gemini-3.8-flash-low",
        "antigravity:gemini-3.8-flash-low",
        "antigravity:gemini-3.8-flash-low",
    ]

    # 2) Strict zero-fallback HTTP 503 verification across ALL 17 AI endpoints when low fails.
    state["fail"] = True
    failing_calls = [
        ("answer", auth_client.post(f"/api/review/{card2_id}/answer", json={"typed_answer": "uncached repair", "latency_ms": 400})),
        ("guide", auth_client.post(f"/api/review/{card1_id}/guide", json={"history": [], "message": "hint"})),
        ("line-hint", auth_client.post(f"/api/review/{card1_id}/line-hint", json={"code": "x = 1", "line_number": 1, "language": "python"})),
        ("weakness-hint", auth_client.post(f"/api/review/{card1_id}/weakness-hint")),
        ("lesson", auth_client.get(f"/api/review/{card2_id}/lesson")),
        ("mutate-prompt", auth_client.post(f"/api/review/{card1_id}/mutate-prompt", json={"mutation_type": "counterfactual"})),
        ("generate-mnemonic", auth_client.post(f"/api/review/{card1_id}/generate-mnemonic")),
        ("predict", auth_client.post(f"/api/review/{card1_id}/predict", json={"prediction": "deleveraging", "confidence": 3})),
        ("contrast-drill", auth_client.post(f"/api/interference/{pair_id}/contrast-drill")),
        ("lexicon/lookup", auth_client.post("/api/lexicon/lookup", json={"term": "Byzantine Quorum Lease", "card_id": card1_id, "deck_name": "Strict Model Deck"})),
        ("code/socratic", auth_client.post(f"/api/code/problems/{slug}/socratic", json={"code": "def quorum(n):\n    return 0", "language": "python", "hint_type": "conceptual"})),
        ("code/explain-selection", auth_client.post("/api/code/explain-selection", json={"selected_code": "deleveraging", "mode": "docs", "deck_id": deck_id})),
        ("code/ask-docs", auth_client.post("/api/code/ask-docs", json={"question": "What drives deleveraging?", "deck_id": deck_id})),
        ("decks/query-docs", auth_client.post(f"/api/decks/{deck_id}/query-docs", json={"query": "deleveraging"})),
        ("extracts/generate-cards", auth_client.post(f"/api/extracts/{ext_id}/generate-cards", json={"max_cards": 1})),
        ("documents/generate-deck", auth_client.post(f"/api/documents/{src_id}/generate-deck", json={"max_cards_per_section": 1})),
        ("memory/decompose", auth_client.post("/api/memory/decompose", json={"front": "Complex Q", "back": "Long answer"})),
    ]

    for label, coro in failing_calls:
        resp = await coro
        assert resp.status_code == 503, f"Expected HTTP 503 for {label} when selected model fails, got {resp.status_code}: {resp.text}"

    assert len(fail_models) >= 17
    assert all(m == "antigravity:gemini-3.8-flash-low" for m in fail_models)
    assert ollama_calls == []


