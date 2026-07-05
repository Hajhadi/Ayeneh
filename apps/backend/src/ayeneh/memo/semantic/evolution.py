"""Knowledge evolution tracking for semantic memory (MEM-03).

Tracks how semantic knowledge changes over time:
- Concept evolution (versioned lineage)
- Knowledge integration
- Knowledge specialization (general → specific)
- Knowledge generalization (specific → broader)
- Semantic drift
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Evolution event types
# ---------------------------------------------------------------------------

EVOLUTION_EVENT_TYPES: list[str] = [
    'created',
    'revised',
    'integrated',
    'specialized',
    'generalized',
    'contradicted',
    'confirmed',
    'deprecated',
    'merged',
    'split',
]

# ---------------------------------------------------------------------------
# Evolution event
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvolutionEvent:
    """A single evolution event in the knowledge lineage."""

    event_id: str
    semantic_memory_id: str
    event_type: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    description: str = ''
    previous_version: str = ''
    new_version: str = ''
    evidence: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Concept lineage
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConceptLineage:
    """Tracks the versioned lineage of a single concept."""

    concept_id: str
    label: str
    events: tuple[EvolutionEvent, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_evolved: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def version_count(self) -> int:
        return len(self.events)

    @property
    def is_active(self) -> bool:
        if not self.events:
            return True
        return self.events[-1].event_type != 'deprecated'


# ---------------------------------------------------------------------------
# Knowledge evolution tracker
# ---------------------------------------------------------------------------


class KnowledgeEvolution:
    """Tracks how semantic knowledge changes over time.

    Maintains concept lineages and records evolution events for
    integration, specialization, generalization, and semantic drift.
    """

    def __init__(self) -> None:
        self._lineages: dict[str, ConceptLineage] = {}
        self._events: list[EvolutionEvent] = []

    @property
    def lineage_count(self) -> int:
        return len(self._lineages)

    @property
    def event_count(self) -> int:
        return len(self._events)

    # ------------------------------------------------------------------
    # Lineage management
    # ------------------------------------------------------------------

    def get_lineage(self, concept_id: str) -> ConceptLineage | None:
        """Retrieve the lineage for a concept."""
        return self._lineages.get(concept_id)

    def list_lineages(self, active_only: bool = False) -> list[ConceptLineage]:
        """List all concept lineages."""
        lineages = list(self._lineages.values())
        if active_only:
            lineages = [l for l in lineages if l.is_active]
        return lineages

    # ------------------------------------------------------------------
    # Evolution tracking
    # ------------------------------------------------------------------

    def record_creation(
        self,
        event_id: str,
        semantic_memory_id: str,
        label: str,
        description: str = '',
        evidence: tuple[str, ...] = (),
    ) -> EvolutionEvent:
        """Record the creation of a new concept."""
        event = EvolutionEvent(
            event_id=event_id,
            semantic_memory_id=semantic_memory_id,
            event_type='created',
            description=description,
            new_version='1.0',
            evidence=evidence,
        )
        self._events.append(event)

        lineage = ConceptLineage(
            concept_id=semantic_memory_id,
            label=label,
            events=(event,),
            created_at=event.timestamp,
            last_evolved=event.timestamp,
        )
        self._lineages[semantic_memory_id] = lineage
        return event

    def record_revision(
        self,
        event_id: str,
        semantic_memory_id: str,
        description: str = '',
        evidence: tuple[str, ...] = (),
    ) -> EvolutionEvent:
        """Record a revision to an existing concept."""
        lineage = self._lineages.get(semantic_memory_id)
        prev_version = f"1.{lineage.version_count}" if lineage else '1.0'
        new_version = f"1.{lineage.version_count + 1}" if lineage else '1.1'

        event = EvolutionEvent(
            event_id=event_id,
            semantic_memory_id=semantic_memory_id,
            event_type='revised',
            description=description,
            previous_version=prev_version,
            new_version=new_version,
            evidence=evidence,
        )
        self._events.append(event)

        if lineage is not None:
            updated = ConceptLineage(
                concept_id=lineage.concept_id,
                label=lineage.label,
                events=lineage.events + (event,),
                created_at=lineage.created_at,
                last_evolved=event.timestamp,
            )
            self._lineages[semantic_memory_id] = updated

        return event

    def record_integration(
        self,
        event_id: str,
        semantic_memory_id: str,
        source_concepts: tuple[str, ...] = (),
        description: str = '',
    ) -> EvolutionEvent:
        """Record knowledge integration (merging multiple concepts)."""
        event = EvolutionEvent(
            event_id=event_id,
            semantic_memory_id=semantic_memory_id,
            event_type='integrated',
            description=description or f"Integrated from {len(source_concepts)} sources",
            metadata={'source_concepts': source_concepts},
        )
        self._events.append(event)
        self._update_lineage(semantic_memory_id, event)
        return event

    def record_specialization(
        self,
        event_id: str,
        semantic_memory_id: str,
        parent_concept_id: str,
        description: str = '',
    ) -> EvolutionEvent:
        """Record knowledge specialization (general → specific)."""
        event = EvolutionEvent(
            event_id=event_id,
            semantic_memory_id=semantic_memory_id,
            event_type='specialized',
            description=description or f"Specialized from {parent_concept_id}",
            metadata={'parent_concept': parent_concept_id},
        )
        self._events.append(event)
        self._update_lineage(semantic_memory_id, event)
        return event

    def record_generalization(
        self,
        event_id: str,
        semantic_memory_id: str,
        child_concept_ids: tuple[str, ...] = (),
        description: str = '',
    ) -> EvolutionEvent:
        """Record knowledge generalization (specific → broader)."""
        event = EvolutionEvent(
            event_id=event_id,
            semantic_memory_id=semantic_memory_id,
            event_type='generalized',
            description=description or f"Generalized from {len(child_concept_ids)} specifics",
            metadata={'child_concepts': child_concept_ids},
        )
        self._events.append(event)
        self._update_lineage(semantic_memory_id, event)
        return event

    def record_semantic_drift(
        self,
        event_id: str,
        semantic_memory_id: str,
        drift_description: str,
        evidence: tuple[str, ...] = (),
    ) -> EvolutionEvent:
        """Record semantic drift (meaning change over time)."""
        event = EvolutionEvent(
            event_id=event_id,
            semantic_memory_id=semantic_memory_id,
            event_type='revised',
            description=f"Semantic drift: {drift_description}",
            evidence=evidence,
            metadata={'drift': True},
        )
        self._events.append(event)
        self._update_lineage(semantic_memory_id, event)
        return event

    def record_deprecation(
        self,
        event_id: str,
        semantic_memory_id: str,
        reason: str = '',
    ) -> EvolutionEvent:
        """Record deprecation of a concept."""
        event = EvolutionEvent(
            event_id=event_id,
            semantic_memory_id=semantic_memory_id,
            event_type='deprecated',
            description=reason or 'Deprecated',
        )
        self._events.append(event)
        self._update_lineage(semantic_memory_id, event)
        return event

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_events_for_concept(self, concept_id: str) -> list[EvolutionEvent]:
        """Get all evolution events for a concept, in order."""
        return sorted(
            [e for e in self._events if e.semantic_memory_id == concept_id],
            key=lambda e: e.timestamp,
        )

    def get_events_by_type(self, event_type: str) -> list[EvolutionEvent]:
        """Get all evolution events of a given type."""
        return [e for e in self._events if e.event_type == event_type]

    def get_specializations(self, parent_id: str) -> list[ConceptLineage]:
        """Find all concepts specialized from a parent."""
        results: list[ConceptLineage] = []
        for event in self._events:
            if (
                event.event_type == 'specialized'
                and event.metadata.get('parent_concept') == parent_id
            ):
                lineage = self._lineages.get(event.semantic_memory_id)
                if lineage is not None:
                    results.append(lineage)
        return results

    def get_generalizations(self, child_id: str) -> list[ConceptLineage]:
        """Find all concepts that generalized from a child."""
        results: list[ConceptLineage] = []
        for event in self._events:
            if event.event_type == 'generalized':
                children = event.metadata.get('child_concepts', ())
                if child_id in children:
                    lineage = self._lineages.get(event.semantic_memory_id)
                    if lineage is not None:
                        results.append(lineage)
        return results

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        """Return a summary of the evolution tracker."""
        type_counts: dict[str, int] = {}
        for event in self._events:
            type_counts[event.event_type] = type_counts.get(event.event_type, 0) + 1
        return {
            'total_lineages': self.lineage_count,
            'total_events': self.event_count,
            'events_by_type': type_counts,
            'active_lineages': sum(1 for l in self._lineages.values() if l.is_active),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_lineage(self, concept_id: str, event: EvolutionEvent) -> None:
        """Update or create a lineage with a new event."""
        existing = self._lineages.get(concept_id)
        if existing is not None:
            updated = ConceptLineage(
                concept_id=existing.concept_id,
                label=existing.label,
                events=existing.events + (event,),
                created_at=existing.created_at,
                last_evolved=event.timestamp,
            )
            self._lineages[concept_id] = updated
        else:
            lineage = ConceptLineage(
                concept_id=concept_id,
                label=event.description[:50] if event.description else concept_id,
                events=(event,),
                created_at=event.timestamp,
                last_evolved=event.timestamp,
            )
            self._lineages[concept_id] = lineage
