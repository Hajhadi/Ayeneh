"""Execution context — runtime's working data structure for a single request."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ayeneh.agents.base import AgentOutput


class RuntimeState(StrEnum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPOSING = "composing"
    RESPONDING = "responding"
    ABORTING = "aborting"
    TIMING_OUT = "timing_out"
    FAILED = "failed"


@dataclass
class StepTrace:
    """Trace record for a single step execution."""

    step_id: str
    agent_name: str
    status: str = "pending"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int = 0
    retry_count: int = 0
    error: str | None = None


@dataclass
class RuntimeEvent:
    """A recorded runtime event."""

    event_type: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionContext:
    """Per-request working data structure.

    Immutable request data — set once, never modified:
    - request_id, user_id, conversation_id
    - user_message, request metadata
    - user profile, conversation history

    Mutable runtime state — modified by Executor:
    - execution plan, agent outputs, step traces
    - accumulated context (memories, knowledge, prompt, response)
    - event log, error log
    """

    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    conversation_id: str = ""
    user_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    user_profile: dict[str, Any] = field(default_factory=dict)
    conversation_history: list[dict[str, str]] = field(default_factory=list)

    # Mutable state
    state: RuntimeState = RuntimeState.IDLE
    agent_outputs: dict[str, AgentOutput] = field(default_factory=dict)
    accumulated: dict[str, Any] = field(default_factory=dict)
    step_traces: list[StepTrace] = field(default_factory=list)
    event_log: list[RuntimeEvent] = field(default_factory=list)
    error_log: list[dict[str, Any]] = field(default_factory=list)
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    cancelled: bool = False

    def record_event(self, event_type: str, payload: dict[str, Any] | None = None) -> RuntimeEvent:
        event = RuntimeEvent(event_type=event_type, payload=payload or {})
        self.event_log.append(event)
        return event

    def record_error(self, step_id: str, error: str) -> None:
        self.error_log.append({"step_id": step_id, "error": error, "timestamp": datetime.now(UTC).isoformat()})

    def get_agent_output(self, step_id: str) -> AgentOutput | None:
        return self.agent_outputs.get(step_id)

    def has_output(self, step_id: str) -> bool:
        return step_id in self.agent_outputs

    def cancel(self) -> None:
        self.cancelled = True
        self.state = RuntimeState.ABORTING
