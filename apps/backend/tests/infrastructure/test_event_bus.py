"""Tests for in-memory event bus."""

from __future__ import annotations

import pytest

from ayeneh.infrastructure.repositories.event_bus import InMemoryEventBus


@pytest.mark.asyncio
async def test_publish_and_subscribe() -> None:
    bus = InMemoryEventBus()
    received: list[dict] = []

    async def handler(payload: dict) -> None:
        received.append(payload)

    bus.subscribe("test_event", handler)
    await bus.publish("test_event", {"key": "value"})
    assert len(received) == 1
    assert received[0]["key"] == "value"
