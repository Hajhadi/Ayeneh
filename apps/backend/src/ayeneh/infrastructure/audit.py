"""Structured audit logging — records every security-relevant operation."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger("audit")


@dataclass
class AuditEvent:
    event_id: str
    event_type: str
    user_id: str
    resource_type: str
    resource_id: str
    action: str
    status: str
    ip_address: str = ""
    user_agent: str = ""
    duration_ms: float = 0.0
    detail: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class AuditLogger:
    """Structured audit log for compliance and security monitoring.

    Every mutation operation must call audit_log() to create an entry.
    """

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def log(
        self,
        *,
        event_type: str,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        status: str = "success",
        ip_address: str = "",
        user_agent: str = "",
        duration_ms: float = 0.0,
        detail: dict[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            duration_ms=duration_ms,
            detail=detail or {},
        )
        self._events.append(event)

        logger.info(
            "audit_event",
            event_id=event.event_id,
            event_type=event.event_type,
            user_id=event.user_id,
            resource=f"{event.resource_type}/{event.resource_id}",
            action=event.action,
            status=event.status,
            duration_ms=event.duration_ms,
        )
        return event

    def get_events(
        self,
        *,
        user_id: str | None = None,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        events = self._events
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def get_event_count(self, event_type: str | None = None) -> int:
        if event_type:
            return sum(1 for e in self._events if e.event_type == event_type)
        return len(self._events)
