"""In-memory event bus implementation."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

import structlog

from ayeneh.application.ports.event_bus import EventBus

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = structlog.get_logger(__name__)


class InMemoryEventBus(EventBus):
    """In-memory event bus for development and testing."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[..., Awaitable[None]]]] = defaultdict(list)

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        logger.info("event_published", event_type=event_type)
        for handler in self._handlers.get(event_type, []):
            try:
                await handler(payload)
            except Exception:
                logger.exception("event_handler_failed", event_type=event_type)

    def subscribe(self, event_type: str, handler: Callable[..., Awaitable[None]]) -> None:
        self._handlers[event_type].append(handler)
