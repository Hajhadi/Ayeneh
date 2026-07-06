"""INT-02 Global Context Manager — domain types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


CONTEXT_DIMENSIONS = [
    'temporal',
    'spatial',
    'conversational',
    'behavioral',
    'strategic',
    'operational',
    'social',
    'environmental',
]

CONTEXT_PERSISTENCE = [
    'transient',
    'session',
    'workflow',
    'persistent',
    'historical',
]

HIERARCHICAL_LEVELS = [
    'global',
    'domain',
    'project',
    'workflow',
    'task',
    'immediate',
]


@dataclass(frozen=True)
class ContextEntry:
    """A single context entry from a specific dimension."""

    entry_id: str = ''
    dimension: str = 'operational'
    level: str = 'task'
    persistence: str = 'session'
    content: dict[str, Any] = field(default_factory=dict)
    source_module: str = ''
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.dimension not in CONTEXT_DIMENSIONS:
            raise ValueError(
                f"Invalid dimension: {self.dimension!r}. "
                f"Must be one of {CONTEXT_DIMENSIONS}"
            )
        if self.persistence not in CONTEXT_PERSISTENCE:
            raise ValueError(
                f"Invalid persistence: {self.persistence!r}. "
                f"Must be one of {CONTEXT_PERSISTENCE}"
            )
        if self.level not in HIERARCHICAL_LEVELS:
            raise ValueError(
                f"Invalid level: {self.level!r}. "
                f"Must be one of {HIERARCHICAL_LEVELS}"
            )


@dataclass(frozen=True)
class ContextConflict:
    """A detected conflict between context entries."""

    conflict_id: str = ''
    entry_a_id: str = ''
    entry_b_id: str = ''
    conflict_type: str = ''  # 'contradiction', 'outdated', 'incomplete', 'ambiguous'
    dimension: str = ''
    severity: str = 'low'  # 'low', 'medium', 'high', 'critical'
    resolution_strategy: str = ''
    description: str = ''


@dataclass(frozen=True)
class ContextPriority:
    """Priority assignment for a context entry."""

    entry_id: str = ''
    priority_score: float = 0.0
    reason: str = ''
    factor_breakdown: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ContextDistribution:
    """Record of context distributed to a module."""

    module_id: str = ''
    entries: tuple[str, ...] = ()
    distribution_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    acknowledgement: bool = False


@dataclass(frozen=True)
class ExplainabilityMetadata:
    """Metadata supporting explanation of context management decisions."""

    reasoning_chain: tuple[str, ...] = ()
    contributing_factors: tuple[dict[str, Any], ...] = ()
    confidence_decomposition: dict[str, float] = field(default_factory=dict)
    decision_points: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class GlobalContextObject:
    """Core domain object representing the global context state."""

    context_id: str
    current_goals: tuple[str, ...] = ()
    active_workflows: tuple[str, ...] = ()
    relevant_memory_references: tuple[str, ...] = ()
    dialogue_state: str = ''
    environmental_context: dict[str, Any] = field(default_factory=dict)
    temporal_context: dict[str, Any] = field(default_factory=dict)
    task_context: dict[str, Any] = field(default_factory=dict)
    priority_map: dict[str, float] = field(default_factory=dict)
    known_constraints: tuple[dict[str, Any], ...] = ()
    confidence: float = 0.0
    revision_history: tuple[dict[str, Any], ...] = ()
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    explainability_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GlobalContextResult:
    """Complete result from the GlobalContextManager pipeline."""

    context_id: str = ''
    context_object: GlobalContextObject | None = None
    entries: tuple[ContextEntry, ...] = ()
    conflicts: tuple[ContextConflict, ...] = ()
    priorities: tuple[ContextPriority, ...] = ()
    distributions: tuple[ContextDistribution, ...] = ()
    confidence: float = 0.0
    duration_ms: float = 0.0
    errors: tuple[str, ...] = ()

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0

    @property
    def entry_count(self) -> int:
        return len(self.entries)
