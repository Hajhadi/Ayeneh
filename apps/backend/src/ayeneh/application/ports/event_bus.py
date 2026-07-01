"""Event bus port — publish and subscribe to domain events."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class EventBus(ABC):
    """Abstract event bus interface."""

    @abstractmethod
    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """Publish a domain event."""

    @abstractmethod
    def subscribe(self, event_type: str, handler: Callable[..., Awaitable[None]]) -> None:
        """Register a handler for an event type."""
