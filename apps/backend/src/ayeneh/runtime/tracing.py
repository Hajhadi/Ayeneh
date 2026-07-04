"""Metrics and Trace Recording — per SPEC-01A §13, §36-38.

Every stage emits structured execution events.
Every artifact includes provenance metadata.
Timing is standardized across the system.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Execution Event (SPEC-01A §38)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExecutionEvent:
    """Structured execution event emitted by every stage.

    Per SPEC-01A §38: every stage shall emit structured execution events.
    """

    stage_id: str
    execution_state: str  # running | completed | failed
    artifact_ids: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    provider: str = ""
    cache_status: str = "miss"  # hit | miss | bypass
    success: bool = True
    failure_category: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))


# ---------------------------------------------------------------------------
# Stage Timing (SPEC-01A §36)
# ---------------------------------------------------------------------------


@dataclass
class StageTiming:
    """Timing breakdown for a single stage.

    Per SPEC-01A §36: each stage reports queue, execution, provider,
    serialization, cache, and total duration.
    """

    queue_duration_ms: float = 0.0
    execution_duration_ms: float = 0.0
    provider_duration_ms: float = 0.0
    serialization_duration_ms: float = 0.0
    cache_duration_ms: float = 0.0

    @property
    def total_duration_ms(self) -> float:
        """Total duration = queue + execution + provider + serialization."""
        return (
            self.queue_duration_ms
            + self.execution_duration_ms
            + self.provider_duration_ms
            + self.serialization_duration_ms
        )


# ---------------------------------------------------------------------------
# Provenance Record (SPEC-01A §37)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProvenanceRecord:
    """Provenance metadata for an artifact.

    Per SPEC-01A §37: every artifact shall include provenance.
    """

    producing_stage: str
    producing_module: str
    session_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    engine_version: str = "1.0.0"
    policy_version: str = "0.0.0"
    originating_artifacts: list[str] = field(default_factory=list)
    provider_id: str = ""
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))


# ---------------------------------------------------------------------------
# Trace Recording (SPEC-01A §28)
# ---------------------------------------------------------------------------


@dataclass
class TraceRecord:
    """Complete trace for a runtime session.

    Per SPEC-01A §28: a Runtime Session is complete only when
    trace information has been stored.
    """

    session_id: str = ""
    events: list[ExecutionEvent] = field(default_factory=list)
    provenance_records: list[ProvenanceRecord] = field(default_factory=list)
    total_duration_ms: float = 0.0
    stages_completed: int = 0
    stages_failed: int = 0
    artifacts_produced: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class TraceRecorder:
    """Collects execution events, timing, and provenance for a session.

    Per SPEC-01A §38: observability events are mandatory.
    Logging alone is insufficient.
    """

    def __init__(self, session_id: str = "") -> None:
        self._session_id = session_id
        self._events: list[ExecutionEvent] = []
        self._provenance: list[ProvenanceRecord] = []
        self._artifacts: list[str] = []

    def record_event(
        self,
        stage_id: str,
        state: str,
        duration_ms: float = 0.0,
        provider: str = "",
        cache_status: str = "miss",
        success: bool = True,
        failure_category: str | None = None,
        artifact_ids: list[str] | None = None,
    ) -> ExecutionEvent:
        """Record a structured execution event."""
        event = ExecutionEvent(
            stage_id=stage_id,
            execution_state=state,
            duration_ms=duration_ms,
            provider=provider,
            cache_status=cache_status,
            success=success,
            failure_category=failure_category,
            artifact_ids=artifact_ids or [],
        )
        self._events.append(event)

        if artifact_ids:
            self._artifacts.extend(artifact_ids)

        logger.debug(
            "execution_event_recorded",
            stage_id=stage_id,
            state=state,
            duration_ms=duration_ms,
        )

        return event

    def record_provenance(
        self,
        producing_stage: str,
        producing_module: str,
        engine_version: str = "1.0.0",
        policy_version: str = "0.0.0",
        originating_artifacts: list[str] | None = None,
        provider_id: str = "",
    ) -> ProvenanceRecord:
        """Record provenance for an artifact."""
        record = ProvenanceRecord(
            producing_stage=producing_stage,
            producing_module=producing_module,
            session_id=self._session_id,
            engine_version=engine_version,
            policy_version=policy_version,
            originating_artifacts=originating_artifacts or [],
            provider_id=provider_id,
        )
        self._provenance.append(record)
        return record

    def build_trace(self, total_duration_ms: float = 0.0) -> TraceRecord:
        """Build complete trace record for the session."""
        return TraceRecord(
            session_id=self._session_id,
            events=list(self._events),
            provenance_records=list(self._provenance),
            total_duration_ms=total_duration_ms,
            stages_completed=sum(1 for e in self._events if e.execution_state == "completed"),
            stages_failed=sum(1 for e in self._events if e.execution_state == "failed"),
            artifacts_produced=list(self._artifacts),
        )

    def get_events(self) -> list[ExecutionEvent]:
        """Get all recorded events."""
        return list(self._events)

    def get_provenance(self) -> list[ProvenanceRecord]:
        """Get all provenance records."""
        return list(self._provenance)
