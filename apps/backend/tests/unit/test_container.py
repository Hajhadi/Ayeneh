"""Tests for dependency injection container."""

from __future__ import annotations

from ayeneh.container import Container


def test_container_initializes() -> None:
    container = Container()
    container.initialize()
    assert container.planner is not None
    assert container.executor is not None
    assert container.event_bus is not None
    assert container.conversation_agent is not None
    assert container.memory_agent is not None
