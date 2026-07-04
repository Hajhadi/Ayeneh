"""RuntimeSession and RuntimeContext — per SPEC-01A Part 1 §8-9.

RuntimeSession: Represents one complete pipeline execution.
RuntimeContext: Immutable state shared across stages.

All fields are immutable after creation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# RuntimeSession (SPEC-01A §9)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RuntimeSession:
    """One complete execution of the pipeline for a single request.

    All fields are immutable throughout execution.
    """

    # Identity (required)
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Context (optional, if available)
    user_context_id: str | None = None
    conversation_id: str | None = None

    # Configuration
    product_profile: str = "ayeneh"
    active_policy: str = "default"

    # Provider selection
    selected_providers: dict[str, str] = field(default_factory=dict)

    # Version tracking
    knowledge_version: str = "0.0.0"
    graph_version: str = "0.0.0"
    policy_version: str = "0.0.0"
    provider_version: str = "0.0.0"
    interpretation_version: str = "0.0.0"
    reasoning_version: str = "0.0.0"
    router_version: str = "0.0.0"


# ---------------------------------------------------------------------------
# Runtime Artifact Reference (SPEC-01A §5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArtifactRef:
    """Reference to an immutable runtime artifact."""

    artifact_type: str  # e.g. "QueryAnalysis", "RetrievalPlan"
    owner: str  # producing stage
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Runtime Context (SPEC-01A §8)
# ---------------------------------------------------------------------------


@dataclass
class RuntimeContext:
    """Immutable state shared across stages.

    The Runtime Context is the only object allowed to travel across stages.
    Every field must have: owner, type, version, provenance.

    Contains references to immutable runtime artifacts.
    Never contains mutable global variables, hidden caches,
    provider-specific state, or undocumented objects.
    """

    # Session reference
    session: RuntimeSession = field(default_factory=RuntimeSession)

    # Input
    user_message: str = ""
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    uploaded_files: list[dict[str, Any]] = field(default_factory=list)

    # Artifact references (populated by stages)
    artifacts: dict[str, ArtifactRef] = field(default_factory=dict)

    # Stage-specific data (mutable during execution, but only by owning stage)
    query_analysis: Any = None
    retrieval_plan: Any = None
    retrieved_knowledge: Any = None
    integrated_knowledge: Any = None
    reasoning_result: Any = None
    interpretation_result: Any = None
    safety_report: Any = None
    response_draft: Any = None
    final_response: Any = None

    def register_artifact(self, artifact_type: str, owner: str, version: str = "1.0.0") -> ArtifactRef:
        """Register an artifact produced by a stage."""
        ref = ArtifactRef(artifact_type=artifact_type, owner=owner, version=version)
        self.artifacts[artifact_type] = ref
        return ref

    def get_artifact(self, artifact_type: str) -> ArtifactRef | None:
        """Get a registered artifact reference."""
        return self.artifacts.get(artifact_type)


# ---------------------------------------------------------------------------
# Runtime State Machine (SPEC-01A §16)
# ---------------------------------------------------------------------------


class RuntimeState:
    """Pipeline execution states per SPEC-01A §16."""

    NEW = "new"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    RETRIEVING = "retrieving"
    REASONING = "reasoning"
    INTERPRETING = "interpreting"
    VALIDATING = "validating"
    GENERATING = "generating"
    STREAMING = "streaming"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Runtime Metrics (SPEC-01A §13, §36, §38)
# ---------------------------------------------------------------------------


@dataclass
class StageMetrics:
    """Observable metrics for a single stage per SPEC-01A §13."""

    stage_name: str
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None
    duration_ms: float = 0.0
    owner: str = ""
    provider: str = ""
    version: str = ""
    cache_status: str = "miss"  # hit | miss | bypass
    success: bool = True
    failure_category: str | None = None
    artifacts_produced: list[str] = field(default_factory=list)

    def complete(self) -> None:
        """Mark stage as completed."""
        self.end_time = datetime.now(UTC)
        if self.start_time:
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000

    def fail(self, category: str) -> None:
        """Mark stage as failed."""
        self.success = False
        self.failure_category = category
        self.complete()


@dataclass
class RuntimeMetrics:
    """Aggregated metrics for a complete runtime session."""

    session_id: str = ""
    total_duration_ms: float = 0.0
    stages: list[StageMetrics] = field(default_factory=list)
    graph_version: str = ""
    knowledge_version: str = ""
    policy_version: str = ""
    provider_version: str = ""
    interpretation_version: str = ""
    reasoning_version: str = ""
    router_version: str = ""

    def add_stage(self, metrics: StageMetrics) -> None:
        """Add stage metrics."""
        self.stages.append(metrics)

    def finalize(self) -> None:
        """Compute total duration from stages."""
        if self.stages:
            earliest = min(s.start_time for s in self.stages if s.start_time)
            latest = max(s.end_time for s in self.stages if s.end_time)
            if earliest and latest:
                self.total_duration_ms = (latest - earliest).total_seconds() * 1000
