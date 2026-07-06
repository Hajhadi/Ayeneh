"""INT-01 Cognitive Orchestrator — domain types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


ORCHESTRATION_STATUSES = [
    'pending',
    'analyzing',
    'selecting_modules',
    'resolving_dependencies',
    'scheduling',
    'coordinating',
    'integrating',
    'completed',
    'failed',
    'cancelled',
]

MODULE_CAPABILITIES = [
    'memory_management',
    'dialogue_processing',
    'decision_making',
    'inference',
    'knowledge_retrieval',
    'cognitive_modeling',
    'goal_management',
    'epistemic_safety',
    'provenance_tracking',
    'observability',
]

EXECUTION_STRATEGIES = [
    'sequential',
    'parallel',
    'pipeline',
    'conditional',
    'adaptive',
    'fallback',
]


@dataclass(frozen=True)
class ModuleSelection:
    """Represents a selected module and its role in the orchestration."""

    module_id: str = ''
    capability: str = ''
    priority: float = 0.0
    estimated_cost: float = 0.0
    selection_reasoning: str = ''
    alternatives: tuple[str, ...] = ()


@dataclass(frozen=True)
class DependencyEdge:
    """A single dependency relationship between orchestration steps."""

    source: str = ''
    target: str = ''
    dependency_type: str = 'data'  # 'data', 'control', 'temporal'
    weight: float = 1.0
    is_critical: bool = True


@dataclass(frozen=True)
class ExecutionStep:
    """A single step in the execution schedule."""

    step_id: str = ''
    module_id: str = ''
    action: str = ''
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    strategy: str = 'sequential'
    estimated_duration_ms: float = 0.0
    status: str = 'pending'


@dataclass(frozen=True)
class CoordinationMessage:
    """Message passed between modules during cross-module coordination."""

    source_module: str = ''
    target_module: str = ''
    message_type: str = 'data'
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class IntegrationResult:
    """Aggregated result from all module outputs."""

    module_outputs: dict[str, Any] = field(default_factory=dict)
    conflicts: tuple[dict[str, Any], ...] = ()
    merged_summary: str = ''
    confidence: float = 0.0


@dataclass(frozen=True)
class ExplainabilityMetadata:
    """Metadata supporting explanation of orchestration decisions."""

    reasoning_chain: tuple[str, ...] = ()
    contributing_factors: tuple[dict[str, Any], ...] = ()
    confidence_decomposition: dict[str, float] = field(default_factory=dict)
    alternative_interpretations: tuple[str, ...] = ()
    decision_points: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class OrchestrationObject:
    """Core domain object for a cognitive orchestration task."""

    orchestration_id: str
    task_id: str = ''
    participating_modules: tuple[str, ...] = ()
    execution_graph: dict[str, Any] = field(default_factory=dict)
    dependency_graph: dict[str, Any] = field(default_factory=dict)
    execution_timeline: tuple[dict[str, Any], ...] = ()
    current_status: str = 'pending'
    confidence: float = 0.0
    resource_allocation: dict[str, Any] = field(default_factory=dict)
    final_integration_summary: str = ''
    version_history: tuple[dict[str, Any], ...] = ()
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    explainability_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.current_status not in ORCHESTRATION_STATUSES:
            raise ValueError(
                f"Invalid status: {self.current_status!r}. "
                f"Must be one of {ORCHESTRATION_STATUSES}"
            )


@dataclass(frozen=True)
class OrchestrationResult:
    """Complete result from the CognitiveOrchestrator pipeline."""

    orchestration_id: str = ''
    orchestration_object: OrchestrationObject | None = None
    selected_modules: tuple[ModuleSelection, ...] = ()
    execution_steps: tuple[ExecutionStep, ...] = ()
    integration: IntegrationResult | None = None
    confidence: float = 0.0
    duration_ms: float = 0.0
    errors: tuple[str, ...] = ()

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def module_count(self) -> int:
        return len(self.selected_modules)
