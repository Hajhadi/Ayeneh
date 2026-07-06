"""ACT-02 Habit Ecology.

Maps relationships between habits: Supportive, Competing, Neutral,
Resource-sharing, Mutually reinforcing.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from ayeneh.act.habit_formation.types import HabitEcologyRelation

logger = structlog.get_logger(__name__)

RELATION_TYPES: list[str] = [
    'supportive',
    'competing',
    'neutral',
    'resource_sharing',
    'mutually_reinforcing',
]


class HabitEcology:
    """Maps and manages relationships between habits.

    Provides operations to register, query, and analyze
    inter-habit relationships.
    """

    def __init__(self) -> None:
        self._relations: dict[str, HabitEcologyRelation] = {}
        self._habit_index: dict[str, set[str]] = {}

    def register_relation(
        self,
        habit_a: str,
        habit_b: str,
        relation_type: str = 'neutral',
        strength: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> HabitEcologyRelation:
        """Register a relationship between two habits."""
        if relation_type not in RELATION_TYPES:
            relation_type = 'neutral'

        relation = HabitEcologyRelation(
            relation_id=str(uuid.uuid4()),
            habit_a=habit_a,
            habit_b=habit_b,
            relation_type=relation_type,
            strength=max(0.0, min(1.0, strength)),
            metadata=dict(metadata or {}),
        )

        self._relations[relation.relation_id] = relation
        self._habit_index.setdefault(habit_a, set()).add(
            relation.relation_id,
        )
        self._habit_index.setdefault(habit_b, set()).add(
            relation.relation_id,
        )

        logger.debug(
            'act.habit_formation.ecology.relation_registered',
            habit_a=habit_a,
            habit_b=habit_b,
            relation_type=relation_type,
        )
        return relation

    def get_relations_for_habit(
        self, habit_id: str,
    ) -> tuple[HabitEcologyRelation, ...]:
        """Get all relations involving a specific habit."""
        rel_ids = self._habit_index.get(habit_id, set())
        return tuple(
            self._relations[rid]
            for rid in rel_ids
            if rid in self._relations
        )

    def get_relation(
        self, relation_id: str,
    ) -> HabitEcologyRelation | None:
        """Get a specific relation by ID."""
        return self._relations.get(relation_id)

    def find_competitors(
        self, habit_id: str,
    ) -> tuple[str, ...]:
        """Find all habits that compete with the given habit."""
        relations = self.get_relations_for_habit(habit_id)
        competitors: list[str] = []
        for rel in relations:
            if rel.relation_type == 'competing':
                other = (
                    rel.habit_b if rel.habit_a == habit_id
                    else rel.habit_a
                )
                competitors.append(other)
        return tuple(competitors)

    def find_supporters(
        self, habit_id: str,
    ) -> tuple[str, ...]:
        """Find all habits that support the given habit."""
        relations = self.get_relations_for_habit(habit_id)
        supporters: list[str] = []
        for rel in relations:
            if rel.relation_type in ('supportive', 'mutually_reinforcing'):
                other = (
                    rel.habit_b if rel.habit_a == habit_id
                    else rel.habit_a
                )
                supporters.append(other)
        return tuple(supporters)

    def find_resource_sharers(
        self, habit_id: str,
    ) -> tuple[str, ...]:
        """Find all habits sharing resources with the given habit."""
        relations = self.get_relations_for_habit(habit_id)
        sharers: list[str] = []
        for rel in relations:
            if rel.relation_type == 'resource_sharing':
                other = (
                    rel.habit_b if rel.habit_a == habit_id
                    else rel.habit_a
                )
                sharers.append(other)
        return tuple(sharers)

    def compute_ecology_score(
        self, habit_id: str,
    ) -> dict[str, float]:
        """Compute aggregate ecology metrics for a habit."""
        relations = self.get_relations_for_habit(habit_id)

        supportive_strength = 0.0
        competing_strength = 0.0
        neutral_count = 0

        for rel in relations:
            if rel.relation_type in ('supportive', 'mutually_reinforcing'):
                supportive_strength += rel.strength
            elif rel.relation_type == 'competing':
                competing_strength += rel.strength
            elif rel.relation_type == 'neutral':
                neutral_count += 1

        total = max(len(relations), 1)
        return {
            'supportive_strength': supportive_strength / total,
            'competing_strength': competing_strength / total,
            'neutral_ratio': neutral_count / total,
            'total_relations': float(len(relations)),
            'net_support': (
                (supportive_strength - competing_strength) / total
            ),
        }

    def list_all_relations(self) -> tuple[HabitEcologyRelation, ...]:
        """Return all registered relations."""
        return tuple(self._relations.values())

    def remove_relation(self, relation_id: str) -> bool:
        """Remove a relation by ID. Returns True if found and removed."""
        rel = self._relations.pop(relation_id, None)
        if rel is None:
            return False

        a_index = self._habit_index.get(rel.habit_a, set())
        a_index.discard(relation_id)
        b_index = self._habit_index.get(rel.habit_b, set())
        b_index.discard(relation_id)

        logger.debug(
            'act.habit_formation.ecology.relation_removed',
            relation_id=relation_id,
        )
        return True
