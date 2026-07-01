"""Tests for runtime endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.asyncio
async def test_send_message(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/runtime/message",
        json={"content": "hello"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "content" in data
    assert "conversation_id" in data


@pytest.mark.asyncio
async def test_stream_endpoint_returns_sse(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/runtime/message/stream",
        json={"content": "hello"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    body = response.text
    assert "event: message_start" in body
    assert "event: content_delta" in body
    assert "event: message_end" in body
    assert "conversation_id" in body


@pytest.mark.asyncio
async def test_stream_includes_conversation_id(client: AsyncClient) -> None:
    conv_id = "test-conv-123"
    response = await client.post(
        "/api/v1/runtime/message/stream",
        json={"content": "hello", "conversation_id": conv_id},
    )
    assert response.status_code == 200
    body = response.text
    assert conv_id in body


@pytest.mark.asyncio
async def test_stream_emits_delta_tokens(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/runtime/message/stream",
        json={"content": "hello"},
    )
    body = response.text
    delta_events = [line for line in body.split("\n") if line.startswith("event: content_delta")]
    assert len(delta_events) > 0
