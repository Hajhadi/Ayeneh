"""Tests for MEMO API endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from ayeneh.api.deps import set_container
from ayeneh.main import app


@pytest.fixture(autouse=True)
def _set_container():
    """Set a mock container where database is None so endpoints use fallback paths."""
    c = MagicMock()
    c.database = None
    set_container(c)
    yield
    set_container(None)


@pytest.fixture()
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestMemoHealth:
    async def test_health(self, client: AsyncClient):
        resp = await client.get("/api/v1/memo/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["module"] == "memo"


# ---------------------------------------------------------------------------
# Episodes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestMemoEpisodes:
    async def test_create_episode(self, client: AsyncClient):
        resp = await client.post("/api/v1/memo/episodes", json={
            "title": "Test Episode",
            "summary": "A test",
            "episode_type": "learning",
            "confidence": 0.8,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test Episode"
        assert data["episode_type"] == "learning"
        assert "id" in data

    async def test_list_episodes(self, client: AsyncClient):
        resp = await client.get("/api/v1/memo/episodes")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "total" in data
        assert data["total"] == 0

    async def test_create_returns_user_id(self, client: AsyncClient):
        resp = await client.post("/api/v1/memo/episodes", json={
            "title": "User ID Test",
            "episode_type": "career",
        })
        data = resp.json()
        assert "user_id" in data
        assert len(data["user_id"]) == 36  # UUID format


# ---------------------------------------------------------------------------
# Semantic
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestMemoSemantic:
    async def test_create_semantic(self, client: AsyncClient):
        resp = await client.post("/api/v1/memo/semantic", json={
            "knowledge_statement": "User prefers dark mode",
            "category": "personal_interests",
            "confidence": 0.9,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["knowledge_statement"] == "User prefers dark mode"
        assert data["category"] == "personal_interests"
        assert data["confidence"] == 0.9

    async def test_list_semantic(self, client: AsyncClient):
        resp = await client.get("/api/v1/memo/semantic")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "total" in data
        assert data["total"] == 0


# ---------------------------------------------------------------------------
# Working Memory
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestMemoWorking:
    async def test_create_working(self, client: AsyncClient):
        resp = await client.post("/api/v1/memo/working", json={
            "source_memory_id": "mem-001",
            "activation_reason": "conversation context",
            "activation_score": 0.8,
            "priority_score": 0.7,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["source_memory_id"] == "mem-001"
        assert data["activation_score"] == 0.8
        assert data["status"] == "active"

    async def test_list_working(self, client: AsyncClient):
        resp = await client.get("/api/v1/memo/working")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert data["total"] == 0


# ---------------------------------------------------------------------------
# Knowledge Graph
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestMemoKnowledgeGraph:
    async def test_create_node(self, client: AsyncClient):
        resp = await client.post("/api/v1/memo/graph/nodes", json={
            "label": "Python",
            "category": "skills",
            "layer": "semantic",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["label"] == "Python"
        assert data["category"] == "skills"
        assert data["layer"] == "semantic"

    async def test_create_edge(self, client: AsyncClient):
        n1 = await client.post("/api/v1/memo/graph/nodes", json={
            "label": "Node A",
            "category": "concepts",
        })
        n2 = await client.post("/api/v1/memo/graph/nodes", json={
            "label": "Node B",
            "category": "concepts",
        })
        resp = await client.post("/api/v1/memo/graph/edges", json={
            "source_node_id": n1.json()["id"],
            "target_node_id": n2.json()["id"],
            "relationship": "supports",
            "weight": 0.8,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["relationship"] == "supports"
        assert data["weight"] == 0.8

    async def test_get_graph(self, client: AsyncClient):
        resp = await client.get("/api/v1/memo/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data
        assert data["node_count"] == 0
        assert data["edge_count"] == 0


# ---------------------------------------------------------------------------
# Consolidation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestMemoConsolidation:
    async def test_consolidate(self, client: AsyncClient):
        resp = await client.post("/api/v1/memo/consolidate", json={
            "target_memory_id": "mem-test",
            "decision": "promote",
            "confidence_before": 0.3,
            "confidence_after": 0.8,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["decision"] == "promote"
        assert data["confidence_before"] == 0.3
        assert data["confidence_after"] == 0.8

    async def test_list_consolidations(self, client: AsyncClient):
        resp = await client.get("/api/v1/memo/consolidate")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert data["total"] == 0


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestMemoRetrieval:
    async def test_retrieve(self, client: AsyncClient):
        resp = await client.post("/api/v1/memo/retrieve", json={
            "limit": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "total" in data
        assert data["total"] == 0


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestMemoRanking:
    async def test_rank(self, client: AsyncClient):
        resp = await client.post("/api/v1/memo/rank", json={
            "target_memory_id": "mem-rank-test",
            "task_profile": "Debugging",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["target_memory_id"] == "mem-rank-test"
        assert data["task_profile"] == "Debugging"
        assert data["overall_score"] == 0.0


# ---------------------------------------------------------------------------
# Forgetting
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestMemoForgetting:
    async def test_forget(self, client: AsyncClient):
        resp = await client.post("/api/v1/memo/forget", json={
            "affected_memory_ids": ["mem-1", "mem-2"],
            "compression_strategy": "redundancy",
            "reason": "Redundant information",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["compression_strategy"] == "redundancy"
        assert data["recoverability_status"] == "recoverable"
        assert "mem-1" in data["affected_memory_ids"]

    async def test_forget_default_tier(self, client: AsyncClient):
        resp = await client.post("/api/v1/memo/forget", json={
            "affected_memory_ids": ["mem-3"],
            "compression_strategy": "episode",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["compression_strategy"] == "episode"


# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestMemoVersioning:
    async def test_list_versions(self, client: AsyncClient):
        resp = await client.get("/api/v1/memo/versions")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "total" in data
        assert data["total"] == 0

    async def test_list_versions_with_memory_filter(self, client: AsyncClient):
        resp = await client.get("/api/v1/memo/versions?memory_id=mem-test")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert data["total"] == 0
