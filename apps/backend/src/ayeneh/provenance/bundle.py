"""ProvenanceBundle — immutable provenance object for end-to-end traceability."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from ayeneh.provenance.types import (
    ChunkOrigin,
    DocumentOrigin,
    EdgeOrigin,
    InterpretationOrigin,
    NodeOrigin,
    ReasoningOrigin,
    ResponseMetadata,
    SafetyOrigin,
)


@dataclass(frozen=True)
class ProvenanceBundle:
    """Immutable provenance bundle that propagates through the entire pipeline.

    Every generated statement can be traced back to its origins.
    Provenance is append-only and never discarded.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Document origins
    document: DocumentOrigin = field(default_factory=DocumentOrigin)
    chunks: list[ChunkOrigin] = field(default_factory=list)

    # Knowledge graph origins
    nodes: list[NodeOrigin] = field(default_factory=list)
    edges: list[EdgeOrigin] = field(default_factory=list)

    # Reasoning origins
    reasoning_steps: list[ReasoningOrigin] = field(default_factory=list)

    # Interpretation origins
    interpretations: list[InterpretationOrigin] = field(default_factory=list)

    # Safety origins
    safety_interventions: list[SafetyOrigin] = field(default_factory=list)

    # Engine versions
    engine_versions: dict[str, str] = field(default_factory=dict)

    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def with_document(self, document: DocumentOrigin) -> ProvenanceBundle:
        """Return a new bundle with document origin added."""
        return ProvenanceBundle(
            id=self.id,
            document=document,
            chunks=self.chunks,
            nodes=self.nodes,
            edges=self.edges,
            reasoning_steps=self.reasoning_steps,
            interpretations=self.interpretations,
            safety_interventions=self.safety_interventions,
            engine_versions=self.engine_versions,
            created_at=self.created_at,
            updated_at=datetime.now(UTC).isoformat(),
        )

    def with_chunk(self, chunk: ChunkOrigin) -> ProvenanceBundle:
        """Return a new bundle with chunk origin added."""
        return ProvenanceBundle(
            id=self.id,
            document=self.document,
            chunks=self.chunks + [chunk],
            nodes=self.nodes,
            edges=self.edges,
            reasoning_steps=self.reasoning_steps,
            interpretations=self.interpretations,
            safety_interventions=self.safety_interventions,
            engine_versions=self.engine_versions,
            created_at=self.created_at,
            updated_at=datetime.now(UTC).isoformat(),
        )

    def with_node(self, node: NodeOrigin) -> ProvenanceBundle:
        """Return a new bundle with graph node added."""
        return ProvenanceBundle(
            id=self.id,
            document=self.document,
            chunks=self.chunks,
            nodes=self.nodes + [node],
            edges=self.edges,
            reasoning_steps=self.reasoning_steps,
            interpretations=self.interpretations,
            safety_interventions=self.safety_interventions,
            engine_versions=self.engine_versions,
            created_at=self.created_at,
            updated_at=datetime.now(UTC).isoformat(),
        )

    def with_edge(self, edge: EdgeOrigin) -> ProvenanceBundle:
        """Return a new bundle with graph edge added."""
        return ProvenanceBundle(
            id=self.id,
            document=self.document,
            chunks=self.chunks,
            nodes=self.nodes,
            edges=self.edges + [edge],
            reasoning_steps=self.reasoning_steps,
            interpretations=self.interpretations,
            safety_interventions=self.safety_interventions,
            engine_versions=self.engine_versions,
            created_at=self.created_at,
            updated_at=datetime.now(UTC).isoformat(),
        )

    def with_reasoning(self, step: ReasoningOrigin) -> ProvenanceBundle:
        """Return a new bundle with reasoning step added."""
        return ProvenanceBundle(
            id=self.id,
            document=self.document,
            chunks=self.chunks,
            nodes=self.nodes,
            edges=self.edges,
            reasoning_steps=self.reasoning_steps + [step],
            interpretations=self.interpretations,
            safety_interventions=self.safety_interventions,
            engine_versions=self.engine_versions,
            created_at=self.created_at,
            updated_at=datetime.now(UTC).isoformat(),
        )

    def with_interpretation(self, interp: InterpretationOrigin) -> ProvenanceBundle:
        """Return a new bundle with interpretation added."""
        return ProvenanceBundle(
            id=self.id,
            document=self.document,
            chunks=self.chunks,
            nodes=self.nodes,
            edges=self.edges,
            reasoning_steps=self.reasoning_steps,
            interpretations=self.interpretations + [interp],
            safety_interventions=self.safety_interventions,
            engine_versions=self.engine_versions,
            created_at=self.created_at,
            updated_at=datetime.now(UTC).isoformat(),
        )

    def with_safety(self, safety: SafetyOrigin) -> ProvenanceBundle:
        """Return a new bundle with safety intervention added."""
        return ProvenanceBundle(
            id=self.id,
            document=self.document,
            chunks=self.chunks,
            nodes=self.nodes,
            edges=self.edges,
            reasoning_steps=self.reasoning_steps,
            interpretations=self.interpretations,
            safety_interventions=self.safety_interventions + [safety],
            engine_versions=self.engine_versions,
            created_at=self.created_at,
            updated_at=datetime.now(UTC).isoformat(),
        )

    def with_engine_version(self, engine: str, version: str) -> ProvenanceBundle:
        """Return a new bundle with engine version added."""
        new_versions = dict(self.engine_versions)
        new_versions[engine] = version
        return ProvenanceBundle(
            id=self.id,
            document=self.document,
            chunks=self.chunks,
            nodes=self.nodes,
            edges=self.edges,
            reasoning_steps=self.reasoning_steps,
            interpretations=self.interpretations,
            safety_interventions=self.safety_interventions,
            engine_versions=new_versions,
            created_at=self.created_at,
            updated_at=datetime.now(UTC).isoformat(),
        )

    def get_total_references(self) -> int:
        """Get total number of provenance references."""
        return (
            len(self.chunks)
            + len(self.nodes)
            + len(self.edges)
            + len(self.reasoning_steps)
            + len(self.interpretations)
            + len(self.safety_interventions)
        )

    def to_response_metadata(self) -> ResponseMetadata:
        """Convert to ResponseMetadata for final response."""
        return ResponseMetadata(
            provenance_bundle_id=self.id,
            cited_chunks=[c.chunk_id for c in self.chunks],
            interpretation_ids=[i.interpretation_id for i in self.interpretations],
            graph_nodes=[n.node_id for n in self.nodes],
            graph_edges=[e.edge_id for e in self.edges],
            engine_versions=self.engine_versions,
            timestamp=self.updated_at,
        )


def merge_bundles(*bundles: ProvenanceBundle) -> ProvenanceBundle:
    """Merge multiple provenance bundles into one.

    Merged bundle contains references to every contributing chunk.
    Never lose origin information.
    """
    if not bundles:
        return ProvenanceBundle()

    merged = bundles[0]

    for bundle in bundles[1:]:
        # Merge chunks (avoid duplicates)
        existing_chunk_ids = {c.chunk_id for c in merged.chunks}
        for chunk in bundle.chunks:
            if chunk.chunk_id not in existing_chunk_ids:
                merged = merged.with_chunk(chunk)

        # Merge nodes
        existing_node_ids = {n.node_id for n in merged.nodes}
        for node in bundle.nodes:
            if node.node_id not in existing_node_ids:
                merged = merged.with_node(node)

        # Merge edges
        existing_edge_ids = {e.edge_id for e in merged.edges}
        for edge in bundle.edges:
            if edge.edge_id not in existing_edge_ids:
                merged = merged.with_edge(edge)

        # Merge reasoning steps
        for step in bundle.reasoning_steps:
            merged = merged.with_reasoning(step)

        # Merge interpretations
        existing_interp_ids = {i.interpretation_id for i in merged.interpretations}
        for interp in bundle.interpretations:
            if interp.interpretation_id not in existing_interp_ids:
                merged = merged.with_interpretation(interp)

        # Merge safety interventions
        for safety in bundle.safety_interventions:
            merged = merged.with_safety(safety)

        # Merge engine versions
        for engine, version in bundle.engine_versions.items():
            merged = merged.with_engine_version(engine, version)

    return merged
