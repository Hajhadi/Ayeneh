"""E2E tests — complete user journeys through the API layer."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from ayeneh.main import app


def _uid() -> str:
    return str(uuid.uuid4())[:8]


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_readiness(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/ready")
    assert resp.status_code == 200
    assert "checks" in resp.json()


@pytest.mark.asyncio
async def test_liveness(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_conversation_create_list(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/conversations", json={"title": f"Conv {_uid()}"})
    assert resp.status_code == 201
    conv_id = resp.json()["id"]

    resp = await client.get(f"/api/v1/conversations/{conv_id}")
    assert resp.status_code == 200

    resp = await client.get("/api/v1/conversations")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_message_send(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/conversations", json={"title": "Msg Test"})
    conv_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/conversations/{conv_id}/messages", json={"content": "Hello"})
    assert resp.status_code == 201

    resp = await client.get(f"/api/v1/conversations/{conv_id}/messages")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_conversation_archive(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/conversations", json={"title": "Archive"})
    conv_id = resp.json()["id"]
    resp = await client.post(f"/api/v1/conversations/{conv_id}/archive")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_runtime_message(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/runtime/message", json={"content": "hi"})
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_runtime_stream(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/runtime/message/stream", json={"content": "hi"})
    assert resp.status_code == 200
    assert "event-stream" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_memories(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/memories")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_patterns(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/patterns")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_reflections(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/reflections")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_blind_spots(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/blind-spots")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_library(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/library/books")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_runtime_status(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/runtime/status")
    assert resp.status_code == 200
    assert "status" in resp.json()


@pytest.mark.asyncio
async def test_metrics(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/metrics")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_user_me(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code in (200, 401)


@pytest.mark.asyncio
async def test_concurrent_health(client: AsyncClient) -> None:
    import asyncio
    async def hit() -> int:
        return (await client.get("/api/v1/health")).status_code
    results = await asyncio.gather(*[hit() for _ in range(30)])
    assert all(r == 200 for r in results)


@pytest.mark.asyncio
async def test_concurrent_conversations(client: AsyncClient) -> None:
    import asyncio
    async def create(i: int) -> str:
        r = await client.post("/api/v1/conversations", json={"title": f"Conc {i}"})
        return r.json().get("id", "")
    ids = await asyncio.gather(*[create(i) for i in range(10)])
    assert len(ids) == 10
    assert all(len(i) > 0 for i in ids)


@pytest.mark.asyncio
async def test_full_journey(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/conversations", json={"title": "Journey"})
    conv_id = resp.json()["id"]

    await client.post(f"/api/v1/conversations/{conv_id}/messages", json={"content": "I feel overwhelmed"})
    resp = await client.get(f"/api/v1/conversations/{conv_id}/messages")
    assert resp.status_code == 200

    resp = await client.get("/api/v1/memories")
    assert resp.status_code == 200

    resp = await client.get("/api/v1/patterns")
    assert resp.status_code == 200

    await client.post(f"/api/v1/conversations/{conv_id}/archive")
