"""COG-05 Narrative Network Builder.

Builds and queries the relationships between narratives, supporting
dominant/latent detection, supporting/conflicting lookups, and
network analysis.
"""

from __future__ import annotations

import structlog
from typing import Any

from ayeneh.cog.narrative.types import NarrativeEdge, NarrativeObject

logger = structlog.get_logger(__name__)


class NarrativeNetworkBuilder:
    """Builds and queries a directed graph of narrative relationships (COG-05).

    Maintains nodes (narrative objects) and edges (typed relationships)
    with support for dominance analysis, latent narrative detection,
    and relationship queries.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, NarrativeObject] = {}
        self._edges: list[NarrativeEdge] = []
        self._outgoing: dict[str, list[NarrativeEdge]] = {}
        self._incoming: dict[str, list[NarrativeEdge]] = {}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_narrative(self, narrative: NarrativeObject) -> None:
        """Add or replace a narrative node."""
        self._nodes[narrative.identifier] = narrative
        logger.info('cog.narrative_network.node_added', node_id=narrative.identifier)

    def connect(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        confidence: float = 0.5,
    ) -> None:
        """Create a directed edge between two narratives.

        Raises ValueError if either endpoint does not exist.
        """
        if source_id not in self._nodes:
            raise ValueError(f'Source narrative {source_id!r} not found in network')
        if target_id not in self._nodes:
            raise ValueError(f'Target narrative {target_id!r} not found in network')

        edge = NarrativeEdge(
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
            confidence=confidence,
        )
        self._edges.append(edge)
        self._outgoing.setdefault(source_id, []).append(edge)
        self._incoming.setdefault(target_id, []).append(edge)
        logger.info(
            'cog.narrative_network.edge_added',
            source=source_id,
            target=target_id,
            relationship=relationship,
        )

    def remove_narrative(self, narrative_id: str) -> bool:
        """Remove a narrative and all its incident edges. Returns True if found."""
        if narrative_id not in self._nodes:
            return False

        del self._nodes[narrative_id]

        # Clean up outgoing edges
        outgoing = self._outgoing.pop(narrative_id, [])
        for edge in outgoing:
            self._edges = [e for e in self._edges if e is not edge]
            incoming_list = self._incoming.get(edge.target_id, [])
            self._incoming[edge.target_id] = [e for e in incoming_list if e is not edge]

        # Clean up incoming edges
        incoming = self._incoming.pop(narrative_id, [])
        for edge in incoming:
            self._edges = [e for e in self._edges if e is not edge]
            outgoing_list = self._outgoing.get(edge.source_id, [])
            self._outgoing[edge.source_id] = [e for e in outgoing_list if e is not edge]

        logger.info('cog.narrative_network.node_removed', narrative_id=narrative_id)
        return True

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_narrative(self, identifier: str) -> NarrativeObject | None:
        """Retrieve a narrative by its identifier."""
        return self._nodes.get(identifier)

    def find_dominant(self) -> list[NarrativeObject]:
        """Find narratives with both high influence and high confidence.

        Dominant narratives are those with influence_score >= 0.3 AND confidence >= 0.3.
        Results are sorted by combined score (descending).
        """
        dominant: list[tuple[NarrativeObject, float]] = []
        for no in self._nodes.values():
            if no.influence_score >= 0.3 and no.confidence >= 0.3:
                combined = (no.influence_score + no.confidence) / 2.0
                dominant.append((no, combined))

        dominant.sort(key=lambda x: x[1], reverse=True)
        return [no for no, _ in dominant]

    def find_latent(self) -> list[NarrativeObject]:
        """Find narratives with low recent evidence but still preserved.

        Latent narratives have fewer than 2 supporting evidence items but
        are not in contradicted/archived state.
        """
        latent: list[NarrativeObject] = []
        for no in self._nodes.values():
            if (
                len(no.supporting_evidence) < 2
                and no.lifecycle_state not in ('contradicted', 'archived')
            ):
                latent.append(no)
        return latent

    def get_supporting(self, narrative_id: str) -> list[NarrativeObject]:
        """Return narratives that support (positive edge) the given narrative."""
        if narrative_id not in self._nodes:
            return []

        supporting_ids: set[str] = set()
        for edge in self._incoming.get(narrative_id, []):
            if edge.relationship in ('supports', 'strengthens', 'same_category'):
                supporting_ids.add(edge.source_id)
        for edge in self._outgoing.get(narrative_id, []):
            if edge.relationship in ('supports', 'strengthens', 'same_category'):
                supporting_ids.add(edge.target_id)

        return [self._nodes[nid] for nid in supporting_ids if nid in self._nodes]

    def get_conflicting(self, narrative_id: str) -> list[NarrativeObject]:
        """Return narratives that conflict (negative edge) with the given narrative."""
        if narrative_id not in self._nodes:
            return []

        conflicting_ids: set[str] = set()
        for edge in self._incoming.get(narrative_id, []):
            if edge.relationship in ('contradicts', 'weakens', 'opposes'):
                conflicting_ids.add(edge.source_id)
        for edge in self._outgoing.get(narrative_id, []):
            if edge.relationship in ('contradicts', 'weakens', 'opposes'):
                conflicting_ids.add(edge.target_id)

        return [self._nodes[nid] for nid in conflicting_ids if nid in self._nodes]

    def get_by_type(self, narrative_type: str) -> list[NarrativeObject]:
        """Return all narratives of a specific type."""
        return [no for no in self._nodes.values() if no.narrative_type == narrative_type]

    def get_by_template(self, template: str) -> list[NarrativeObject]:
        """Return all narratives using a specific template."""
        return [no for no in self._nodes.values() if no.template == template]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def node_count(self) -> int:
        """Return the number of narratives."""
        return len(self._nodes)

    def edge_count(self) -> int:
        """Return the number of edges."""
        return len(self._edges)

    def all_narratives(self) -> list[NarrativeObject]:
        """Return all narratives."""
        return list(self._nodes.values())

    def all_edges(self) -> list[NarrativeEdge]:
        """Return all edges."""
        return list(self._edges)
