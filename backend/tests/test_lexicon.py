"""Tests for the Concordance / Lexicon subsystem."""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_lookup_binary_approximations_curated(auth_client: AsyncClient):
    """Verifies user's exact test case: looking up 'binary approximations'."""
    resp = await auth_client.post(
        "/api/lexicon/lookup",
        json={
            "term": "binary approximations",
            "context": "When dealing with numbers that are stored as binary approximations, it's important to order your arithmetic correctly.",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["term"] == "binary approximations"
    assert "binary" in data["definition"].lower()
    assert "0.1 + 0.2" in data["example"]
    assert "floating-point" in data["related_terms"]
    assert data["cached"] is False

    # Second lookup must hit the database cache
    cached_resp = await auth_client.post(
        "/api/lexicon/lookup",
        json={"term": "binary approximations"},
    )
    assert cached_resp.status_code == 200
    assert cached_resp.json()["cached"] is True


@pytest.mark.asyncio
async def test_lookup_custom_term_with_mocked_llm(auth_client: AsyncClient, monkeypatch):
    from app.services.grading_service import GradingService

    async def mock_generate(self, prompt, model=None, thinking_budget=None):
        return json.dumps({
            "definition": "Amortized analysis averages the running time over a sequence of operations.",
            "context_explanation": "For dynamic arrays, occasionally doubling the array takes O(n), but over n insertions it averages to O(1) per operation.",
            "example": "vector.push_back() in C++ or list.append() in Python.",
            "domain": "Algorithms & Data Structures",
            "related_terms": ["dynamic array", "potential method", "aggregate analysis"],
        })

    monkeypatch.setattr(GradingService, "_generate", mock_generate)

    resp = await auth_client.post(
        "/api/lexicon/lookup",
        json={
            "term": "amortized analysis",
            "context": "Dynamic array resizing has O(1) amortized time.",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["term"] == "amortized analysis"
    assert "Amortized analysis averages" in data["definition"]
    assert data["domain"] == "Algorithms & Data Structures"
    assert "dynamic array" in data["related_terms"]

    # Verify recent terms endpoint
    recent_resp = await auth_client.get("/api/lexicon/recent")
    assert recent_resp.status_code == 200
    terms = [item["term"] for item in recent_resp.json()]
    assert "amortized analysis" in terms


@pytest.mark.asyncio
async def test_lookup_non_cs_deck_does_not_force_programming(auth_client: AsyncClient, monkeypatch):
    from app.services.grading_service import GradingService

    captured_prompts = []

    async def mock_generate(self, prompt, model=None, thinking_budget=None):
        captured_prompts.append(prompt)
        return json.dumps({
            "definition": "Un asentamiento es un lugar donde se establece una persona o una comunidad.",
            "context_explanation": "En el contexto de la historia y la geografía española e hispanoamericana, los asentamientos coloniales determinaron la distribución urbana y territorial.",
            "example": "El asentamiento de Santa Fe fue fundado a orillas del río en 1573.",
            "domain": "Historia y Lengua Española",
            "related_terms": ["colonia", "encomienda", "urbanización", "población"],
        })

    monkeypatch.setattr(GradingService, "_generate", mock_generate)

    # Create a non-CS deck (e.g. Spanish 321)
    deck_resp = await auth_client.post(
        "/api/decks",
        json={"name": "SPAN 321 - Cultura y Civilización", "thematic_nature": "Spanish Colonial History"},
    )
    assert deck_resp.status_code == 201
    deck_id = deck_resp.json()["id"]

    note_resp = await auth_client.post(
        "/api/notes",
        json={
            "deck_id": deck_id,
            "template_kind": "basic",
            "field_values": {"Front": "¿Qué es un asentamiento?", "Back": "Un lugar donde se establece una comunidad."},
        },
    )
    card_id = note_resp.json()["cards"][0]["id"]

    resp = await auth_client.post(
        "/api/lexicon/lookup",
        json={
            "term": "asentamiento",
            "card_id": card_id,
            "deck_name": "SPAN 321 - Cultura y Civilización",
            "context": "Durante el siglo XVI, los primeros asentamientos españoles en América se organizaron siguiendo el modelo de cuadrícula.",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["term"] == "asentamiento"
    assert "programming" not in data["definition"].lower()
    assert "python" not in (data["example"] or "").lower()
    assert "Historia" in data["domain"]

    # Verify the system prompt captured had non-CS instructions and deck name
    assert len(captured_prompts) == 1
    prompt = captured_prompts[0]
    assert "CRITICAL DOMAIN & RELEVANCE RULES" in prompt
    assert "SPAN 321" in prompt
