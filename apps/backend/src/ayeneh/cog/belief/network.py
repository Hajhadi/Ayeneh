"""Belief Network Builder — COG-06 support.

Manages inter-belief relationships: supports, conflicts_with, depends_on,
and hierarchy.  Provides traversal helpers for conflict detection and
hierarchical decomposition.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.cog.belief.types import (
    BELIEF_RELATIONSHIP_TYPES,
    BeliefNetwork,
    BeliefObject,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# BeliefNetworkBuilder
# ---------------------------------------------------------------------------


class BeliefNetworkBuilder:
    """Mutable builder for BeliefNetwork instances.

    Accumulates beliefs and edges, then freezes into an immutable
    :class:`BeliefNetwork` via :meth:`build`.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, BeliefObject] = {}
        self._edges: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_belief(self, belief: BeliefObject) -> None:
        """Add a belief node to the network."""
        self._nodes[belief.identifier] = belief
        logger.info('cog.belief_network.node_added', belief_id=belief.identifier)

    def connect(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        confidence: float = 0.5,
    ) -> None:
        """Create a directed edge between two beliefs.

        Raises ``ValueError`` if the relationship type is unknown or if
        either node is missing.
        """
        if relationship not in BELIEF_RELATIONSHIP_TYPES:
            raise ValueError(
                f"Unknown relationship type: {relationship}. "
                f"Valid types: {BELIEF_RELATIONSHIP_TYPES}"
            )
        if source_id not in self._nodes:
            raise ValueError(f"Source belief not found: {source_id}")
        if target_id not in self._nodes:
            raise ValueError(f"Target belief not found: {target_id}")

        self._edges.append({
            'source': source_id,
            'target': target_id,
            'relationship': relationship,
            'confidence': confidence,
        })
        logger.info(
            'cog.belief_network.edge_added',
            source=source_id,
            target=target_id,
            relationship=relationship,
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def find_conflicts(self, belief_id: str) -> list[dict[str, Any]]:
        """Find all beliefs that conflict with the given belief."""
        return [
            e for e in self._edges
            if e['relationship'] == 'conflicts_with'
            and (e['source'] == belief_id or e['target'] == belief_id)
        ]

    def find_supporting(self, belief_id: str) -> list[dict[str, Any]]:
        """Find all beliefs that support the given belief."""
        return [
            e for e in self._edges
            if e['relationship'] == 'supports'
            and (e['source'] == belief_id or e['target'] == belief_id)
        ]

    def get_hierarchy(self) -> dict[str, list[str]]:
        """Return beliefs organised by hierarchy level.

        Level 0 = world-level beliefs (no parent in hierarchy edges).
        Each subsequent level depends on the previous.
        """
        children: dict[str, list[str]] = defaultdict(list)
        parents: set[str] = set()

        for e in self._edges:
            if e['relationship'] == 'hierarchy':
                children[e['source']].append(e['target'])
                parents.add(e['target'])

        roots = [n for n in self._nodes if n not in parents]
        hierarchy: dict[str, list[str]] = {}
        queue: deque[tuple[str, int]] = deque((r, 0) for r in roots)
        visited: set[str] = set()

        while queue:
            node_id, level = queue.popleft()
            if node_id in visited:
                continue
            visited.add(node_id)

            key = f'level_{level}'
            hierarchy.setdefault(key, []).append(node_id)

            for child in children.get(node_id, []):
                queue.append((child, level + 1))

        return hierarchy

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self) -> BeliefNetwork:
        """Freeze the accumulated state into an immutable BeliefNetwork."""
        return BeliefNetwork(
            nodes=dict(self._nodes),
            edges=tuple(self._edges),
        )

    @property
    def node_count(self) -> int:
        """Number of belief nodes."""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """Number of edges."""
        return len(self._edges)
