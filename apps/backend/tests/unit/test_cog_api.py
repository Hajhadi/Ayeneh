"""Tests for COG Cognitive Architecture API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_MESSAGES = [
    {"role": "user", "content": "I believe that honesty is important in life."},
    {"role": "assistant", "content": "That's a core value. Tell me more."},
    {"role": "user", "content": "I always try to be truthful with my friends and family."},
    {"role": "assistant", "content": "How does that value shape your daily decisions?"},
    {"role": "user", "content": "I decided to tell my friend the truth even though it was hard."},
]

EMPTY_MESSAGES: list[dict] = []

PERSIAN_MESSAGES = [
    {"role": "user", "content": "من فکر می‌کنم که صداقت خیلی مهم است."},
    {"role": "assistant", "content": "چرا صداقت برایت مهم است؟"},
    {"role": "user", "content": "همیشه سعی می‌کنم با دوستانم راست بگویم."},
]

SINGLE_MESSAGE = [
    {"role": "user", "content": "I need to learn more about Python programming."},
]


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


class TestCogHealth:
    @pytest.mark.asyncio
    async def test_health_returns_200(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/cog/health")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_health_response_structure(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/cog/health")
        data = resp.json()
        assert data["status"] == "healthy"
        assert "modules" in data
        assert "version" in data

    @pytest.mark.asyncio
    async def test_health_modules_count(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/cog/health")
        assert resp.json()["modules"] == 15


# ---------------------------------------------------------------------------
# Analyze endpoint — happy paths
# ---------------------------------------------------------------------------


class TestCogAnalyze:
    @pytest.mark.asyncio
    async def test_analyze_sample_conversation(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/cog/analyze",
            json={
                "user_id": "test-user-1",
                "messages": SAMPLE_MESSAGES,
                "language": "en",
            },
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_analyze_response_fields(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/cog/analyze",
            json={
                "user_id": "test-user-2",
                "messages": SAMPLE_MESSAGES,
            },
        )
        data = resp.json()
        expected_fields = [
            "conversation_id",
            "evidence_count",
            "beliefs_extracted",
            "narratives_extracted",
            "values_extracted",
            "goals_extracted",
            "identity_components",
            "decisions",
            "patterns",
            "reflections",
            "meta_cognitive_objects",
            "awakening_level",
            "reality_calibration",
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_analyze_evidence_populated(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/cog/analyze",
            json={
                "user_id": "test-user-3",
                "messages": SAMPLE_MESSAGES,
            },
        )
        data = resp.json()
        assert data["evidence_count"] > 0

    @pytest.mark.asyncio
    async def test_analyze_conversation_id_deterministic(self, client: AsyncClient) -> None:
        payload = {"user_id": "test-user-4", "messages": SAMPLE_MESSAGES}
        resp1 = await client.post("/api/v1/cog/analyze", json=payload)
        resp2 = await client.post("/api/v1/cog/analyze", json=payload)
        assert resp1.json()["conversation_id"] == resp2.json()["conversation_id"]


# ---------------------------------------------------------------------------
# Analyze endpoint — edge cases
# ---------------------------------------------------------------------------


class TestCogAnalyzeEdgeCases:
    @pytest.mark.asyncio
    async def test_analyze_empty_conversation(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/cog/analyze",
            json={
                "user_id": "test-user-empty",
                "messages": EMPTY_MESSAGES,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["evidence_count"] == 0
        assert data["beliefs_extracted"] == 0

    @pytest.mark.asyncio
    async def test_analyze_persian_conversation(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/cog/analyze",
            json={
                "user_id": "test-user-fa",
                "messages": PERSIAN_MESSAGES,
                "language": "fa",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["conversation_id"].startswith("conv-")

    @pytest.mark.asyncio
    async def test_analyze_single_message(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/cog/analyze",
            json={
                "user_id": "test-user-single",
                "messages": SINGLE_MESSAGE,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["evidence_count"] >= 0

    @pytest.mark.asyncio
    async def test_analyze_missing_messages(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/cog/analyze",
            json={"user_id": "test-user-no-msgs"},
        )
        assert resp.status_code == 422  # validation error

    @pytest.mark.asyncio
    async def test_analyze_missing_user_id(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/cog/analyze",
            json={"messages": SAMPLE_MESSAGES},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Analyze endpoint — response structure
# ---------------------------------------------------------------------------


class TestCogAnalyzeStructure:
    @pytest.mark.asyncio
    async def test_response_is_integer_counts(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/cog/analyze",
            json={
                "user_id": "test-user-int",
                "messages": SAMPLE_MESSAGES,
            },
        )
        data = resp.json()
        int_fields = [
            "evidence_count", "beliefs_extracted", "narratives_extracted",
            "values_extracted", "goals_extracted", "identity_components",
            "decisions", "patterns", "reflections", "meta_cognitive_objects",
        ]
        for field in int_fields:
            assert isinstance(data[field], int), f"{field} should be int, got {type(data[field])}"

    @pytest.mark.asyncio
    async def test_response_is_float_scores(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/cog/analyze",
            json={
                "user_id": "test-user-float",
                "messages": SAMPLE_MESSAGES,
            },
        )
        data = resp.json()
        assert isinstance(data["awakening_level"], float)
        assert isinstance(data["reality_calibration"], float)

    @pytest.mark.asyncio
    async def test_conversation_id_format(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/cog/analyze",
            json={
                "user_id": "test-user-fmt",
                "messages": SAMPLE_MESSAGES,
            },
        )
        conv_id = resp.json()["conversation_id"]
        assert conv_id.startswith("conv-")

    @pytest.mark.asyncio
    async def test_non_negative_counts(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/cog/analyze",
            json={
                "user_id": "test-user-nonneg",
                "messages": SAMPLE_MESSAGES,
            },
        )
        data = resp.json()
        int_fields = [
            "evidence_count", "beliefs_extracted", "narratives_extracted",
            "values_extracted", "goals_extracted", "identity_components",
            "decisions", "patterns", "reflections", "meta_cognitive_objects",
        ]
        for field in int_fields:
            assert data[field] >= 0, f"{field} should be >= 0, got {data[field]}"
