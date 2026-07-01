"""Runtime event publisher — publishes events through the service layer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from ayeneh.application.ports.event_bus import EventBus
    from ayeneh.runtime.context import ExecutionContext, RuntimeEvent

logger = structlog.get_logger(__name__)


class RuntimeEventPublisher:
    """Publishes runtime events through the EventBus."""

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus

    async def publish(self, ctx: ExecutionContext, event_type: str, payload: dict[str, Any] | None = None) -> RuntimeEvent:
        event = ctx.record_event(event_type, payload)
        full_payload = {"request_id": ctx.request_id, **(payload or {})}
        await self._event_bus.publish(event_type, full_payload)
        logger.debug("event_published", event_type=event_type, request_id=ctx.request_id)
        return event

    async def publish_step_event(self, ctx: ExecutionContext, event_type: str, step_id: str, agent_name: str, extra: dict[str, Any] | None = None) -> RuntimeEvent:
        payload = {"step_id": step_id, "agent": agent_name}
        if extra:
            payload.update(extra)
        return await self.publish(ctx, event_type, payload)
