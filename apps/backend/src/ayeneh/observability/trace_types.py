"""Structured trace types for all runtime modules — per SPEC-01A §36-38.

Every trace is a frozen dataclass (immutable after creation).
All 10 pipeline-specific traces inherit from TraceBase.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Shared types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExecutionTiming:
    """Standardized timing breakdown per SPEC-01A §36."""

    wall_ms: float = 0.0
    queue_ms: float = 0.0
    provider_ms: float = 0.0
    cache_ms: float = 0.0


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TraceBase:
    """Protocol-like base: every trace carries these fields."""

    request_id: str = ""
    execution_id: str = ""
    spec_version: str = "1.0.0"
    config_version: str = "0.0.0"
    timing: ExecutionTiming = field(default_factory=ExecutionTiming)
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Runtime Pipeline Traces (SPEC-21 through SPEC-25, SPEC-30)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QueryTrace(TraceBase):
    """Trace for SPEC-21 Query Understanding pipeline.

    Required fields per AUDIT-21 QUA-014:
    Request ID, Execution ID, Language Analysis, Intent Decisions,
    Concept Matches, Alias Matches, Entity Matches, Complexity Analysis,
    Capability Analysis, Execution Timing, Configuration Version,
    Registry Versions, Warnings, Errors, Specification Version.
    """

    raw_input: str = ""
    language: tuple[str, ...] = ()
    intent: str = ""
    question_type: str = ""
    concepts: tuple[str, ...] = ()
    concept_details: tuple[dict[str, Any], ...] = ()
    alias_matches: tuple[dict[str, Any], ...] = ()
    entities: tuple[str, ...] = ()
    entity_details: tuple[dict[str, Any], ...] = ()
    complexity_level: str = ""
    complexity_scores: dict[str, float] = field(default_factory=dict)
    capabilities: tuple[str, ...] = ()
    reasoning_depth: str = ""
    retrieval_depth: str = ""
    registry_versions: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalPlanningTrace(TraceBase):
    """Trace for SPEC-22 Retrieval Planning pipeline.

    Required fields per AUDIT-22 RPA-012:
    Request ID, Plan ID, QueryAnalysis Reference, Planning Decisions,
    Knowledge Source Selection, Traversal Decisions, Evidence Decisions,
    Capability Analysis, Execution Timing, Configuration Version,
    Warnings, Errors, Specification Version.
    """

    plan_id: str = ""
    query_analysis_ref: str = ""
    strategy: str = ""
    sources_selected: tuple[dict[str, Any], ...] = ()
    evidence_requirements: tuple[dict[str, Any], ...] = ()
    traversal_plan: dict[str, Any] = field(default_factory=dict)
    budget: int = 0
    capability_analysis: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalExecutionTrace(TraceBase):
    """Trace for SPEC-23 Knowledge Retrieval pipeline.

    Required fields: RetrievalPlan, Executed Operations, Knowledge Sources,
    Traversal History, Retrieved Nodes/Edges/Chunks/Citations, Cache Events,
    Execution Timing, Warnings, Errors.
    """

    plan_id: str = ""
    executed_operations: tuple[dict[str, Any], ...] = ()
    knowledge_sources_used: tuple[str, ...] = ()
    retrieved_chunks: int = 0
    retrieved_profiles: int = 0
    retrieved_citations: int = 0
    retrieved_nodes: int = 0
    retrieved_edges: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    validation_passed: bool = True
    duplicates_found: int = 0


@dataclass(frozen=True)
class ReasoningTrace(TraceBase):
    """Trace for SPEC-24 Reasoning pipeline.

    Required fields: Reasoning Mode, Evidence Graph, Intermediate Facts,
    Conflict Analysis, Confidence Evolution, AI Router Decisions,
    Provider Metrics, Execution Timing, Warnings, Errors.
    """

    reasoning_mode: str = ""
    conclusions_count: int = 0
    conflicts_count: int = 0
    evidence_graph_summary: dict[str, Any] = field(default_factory=dict)
    confidence_components: dict[str, float] = field(default_factory=dict)
    intermediate_facts: tuple[dict[str, Any], ...] = ()
    conflict_analysis: tuple[dict[str, Any], ...] = ()
    assumptions_count: int = 0
    uncertainty_statements: tuple[str, ...] = ()
    ai_router_decisions: tuple[dict[str, Any], ...] = ()
    provider_metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResponseTrace(TraceBase):
    """Trace for SPEC-25 Response pipeline.

    Required fields: Validation Results, Formatting Decisions,
    Citation Decisions, Streaming Decisions, Provider Decisions,
    Execution Timing, Warnings, Errors.
    """

    validation_passed: bool = True
    validation_errors: tuple[str, ...] = ()
    validation_warnings: tuple[str, ...] = ()
    citation_count: int = 0
    uncertainty_count: int = 0
    follow_up_count: int = 0
    response_length: int = 0
    formatting_decisions: tuple[dict[str, Any], ...] = ()
    streaming_decisions: tuple[dict[str, Any], ...] = ()
    provider_decisions: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class RouterTrace(TraceBase):
    """Trace for SPEC-30 AI Router.

    Required fields: Task Profile, Provider Ranking, Selected Provider,
    Fallback History, Execution Metrics (Latency, Tokens, Cost),
    Validation Results, Warnings, Errors.
    """

    task_type: str = ""
    selected_provider: str = ""
    selected_model: str = ""
    routing_reason: str = ""
    provider_ranking: tuple[dict[str, Any], ...] = ()
    fallback_used: bool = False
    fallback_history: tuple[str, ...] = ()
    cost_estimate: float = 0.0
    latency_estimate_ms: float = 0.0
    tokens_used: int = 0
    validation_results: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Composite Trace
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RuntimeTrace(TraceBase):
    """Aggregated trace for the full Runtime session.

    Composes all per-stage traces into a single immutable record.
    """

    query_trace: QueryTrace | None = None
    retrieval_plan_trace: RetrievalPlanningTrace | None = None
    retrieval_exec_trace: RetrievalExecutionTrace | None = None
    reasoning_trace: ReasoningTrace | None = None
    response_trace: ResponseTrace | None = None
    router_trace: RouterTrace | None = None
    total_duration_ms: float = 0.0
    stages_completed: int = 0
    stages_failed: int = 0


# ---------------------------------------------------------------------------
# Import Pipeline Traces
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ImportTrace(TraceBase):
    """Trace for import pipeline per SPEC-40."""

    import_id: str = ""
    file_path: str = ""
    file_size: int = 0
    format_detected: str = ""
    stages_completed: tuple[str, ...] = ()
    chunks_created: int = 0
    embeddings_created: int = 0
    status: str = ""  # "completed" | "failed" | "partial"
    error_message: str = ""


@dataclass(frozen=True)
class ExtractionTrace(TraceBase):
    """Trace for concept extraction per SPEC-41."""

    source_text_length: int = 0
    candidates_found: int = 0
    candidates_published: int = 0
    candidates_rejected: int = 0
    confidence_avg: float = 0.0
    languages_detected: tuple[str, ...] = ()
    discovery_sources: tuple[str, ...] = ()


@dataclass(frozen=True)
class NormalizationTrace(TraceBase):
    """Trace for concept normalization per SPEC-35."""

    input_count: int = 0
    resolved_count: int = 0
    unresolved_count: int = 0
    new_canonical_count: int = 0
    aliases_created: int = 0
    average_similarity: float = 0.0


# ---------------------------------------------------------------------------
# Meta-Traces
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ObservabilityTrace(TraceBase):
    """Meta-trace for the observability system itself — per AUDIT-50 OBS-009."""

    subsystems_monitored: int = 0
    trace_count: int = 0
    metrics_snapshot_count: int = 0
    diagnostics_checks: int = 0


@dataclass(frozen=True)
class TelemetryTrace(TraceBase):
    """Meta-trace for telemetry pipeline — per AUDIT-51 MET-009."""

    metric_identifier: str = ""
    telemetry_identifier: str = ""
    aggregation_window_ms: float = 0.0
    publication_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
