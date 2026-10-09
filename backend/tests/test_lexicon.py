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
