"""Integration tests for all V1 API endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from ayeneh.main import app


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Health ──

@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── Conversations ──

@pytest.mark.asyncio
async def test_create_conversation(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/conversations/", json={"title": "Test"})
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["title"] == "Test"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_list_conversations(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/conversations/")
    assert resp.status_code == 200
    assert "data" in resp.json()


@pytest.mark.asyncio
async def test_get_conversation(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/conversations/conv-123")
    assert resp.status_code == 200
    assert resp.json()["id"] == "conv-123"


@pytest.mark.asyncio
async def test_list_messages(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/conversations/conv-123/messages")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_send_message(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/conversations/conv-123/messages",
        json={"content": "Hello world"},
    )
    assert resp.status_code == 201
    assert resp.json()["content"] == "Hello world"


@pytest.mark.asyncio
async def test_update_conversation(client: AsyncClient) -> None:
    resp = await client.patch("/api/v1/conversations/conv-123", json={"title": "Updated"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_archive_conversation(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/conversations/conv-123/archive")
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


# ── Memories ──

@pytest.mark.asyncio
async def test_list_memories(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/memories/")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_search_memories(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/memories/search", json={"query": "test"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_memory(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/memories/mem-123")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_memory(client: AsyncClient) -> None:
    resp = await client.delete("/api/v1/memories/mem-123")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_archive_memory(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/memories/mem-123/archive")
    assert resp.status_code == 200


# ── Patterns ──

@pytest.mark.asyncio
async def test_list_patterns(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/patterns/")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_pattern(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/patterns/pat-123")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_pattern_timeline(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/patterns/pat-123/timeline")
    assert resp.status_code == 200


# ── Reflections ──

@pytest.mark.asyncio
async def test_list_reflections(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/reflections/")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_reflection(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/reflections/ref-123")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_trigger_reflection(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/reflections/", json={})
    assert resp.status_code == 202


# ── Blind Spots ──

@pytest.mark.asyncio
async def test_list_blind_spots(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/blind-spots/")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_blind_spot(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/blind-spots/bs-123")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_trigger_analysis(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/blind-spots/analyze")
    assert resp.status_code == 202


# ── Library ──

@pytest.mark.asyncio
async def test_list_books(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/library/books")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_book(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/library/books/book-123")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_upload_book(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/library/books",
        json={"title": "Test Book", "source_format": "pdf"},
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_delete_book(client: AsyncClient) -> None:
    resp = await client.delete("/api/v1/library/books/book-123")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_reindex_book(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/library/books/book-123/reindex")
    assert resp.status_code == 202


@pytest.mark.asyncio
async def test_get_indexing_progress(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/library/books/book-123/progress")
    assert resp.status_code == 200


# ── Users ──

@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient) -> None:
    resp = await client.patch("/api/v1/users/me", json={"display_name": "New Name"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_user_stats(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/users/me/stats")
    assert resp.status_code == 200


# ── Runtime ──

@pytest.mark.asyncio
async def test_send_runtime_message(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/runtime/message", json={"content": "Hello"})
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_runtime_stream_endpoint(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/runtime/message/stream", json={"content": "Hello"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_runtime_status(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/runtime/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_list_executions(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/runtime/executions")
    assert resp.status_code == 200
