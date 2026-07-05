"""MEM-09 Knowledge Graph integrity validation.

Checks structural invariants, detects anomalies, and reports integrity
violations in the knowledge graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from ayeneh.memo.knowledge_graph.graph import KnowledgeGraph
from ayeneh.memo.knowledge_graph.types import GraphLayer, LAYER_ORDER, NodeCategory, RelationshipCategory


@dataclass(frozen=True)
class IntegrityViolation:
    """A detected violation of graph integrity."""

    violation_type: str = ''
    description: str = ''
    affected_nodes: tuple[str, ...] = ()
    affected_edges: tuple[str, ...] = ()
    severity: str = 'low'  # low, medium, high, critical


@dataclass(frozen=True)
class IntegrityReport:
    """Full integrity report for a knowledge graph."""

    is_valid: bool = True
    violations: tuple[IntegrityViolation, ...] = ()
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    node_count: int = 0
    edge_count: int = 0


def validate_orphan_edges(graph: KnowledgeGraph) -> list[IntegrityViolation]:
    """Check for edges referencing non-existent nodes."""
    violations: list[IntegrityViolation] = []
    for edge in graph._edges.values():
        missing: list[str] = []
        if edge.source_node not in graph._nodes:
            missing.append(edge.source_node)
        if edge.target_node not in graph._nodes:
            missing.append(edge.target_node)
        if missing:
            violations.append(
                IntegrityViolation(
                    violation_type='orphan_edge',
                    description=f'Edge {edge.edge_id} references missing nodes: {missing}',
                    affected_edges=(edge.edge_id,),
                    severity='high',
                )
            )
    return violations


def validate_self_loops(graph: KnowledgeGraph) -> list[IntegrityViolation]:
    """Check for self-loop edges."""
    violations: list[IntegrityViolation] = []
    for edge in graph._edges.values():
        if edge.source_node == edge.target_node:
            violations.append(
                IntegrityViolation(
                    violation_type='self_loop',
                    description=f'Self-loop detected: {edge.edge_id}',
                    affected_edges=(edge.edge_id,),
                    severity='medium',
                )
            )
    return violations


def validate_duplicate_edges(graph: KnowledgeGraph) -> list[IntegrityViolation]:
    """Check for duplicate edges (same source, target, relationship)."""
    seen: dict[str, str] = {}
    violations: list[IntegrityViolation] = []
    for edge in graph._edges.values():
        key = f'{edge.source_node}->{edge.target_node}:{edge.relationship.value}'
        if key in seen:
            violations.append(
                IntegrityViolation(
                    violation_type='duplicate_edge',
                    description=f'Duplicate edge: {edge.edge_id} duplicates {seen[key]}',
                    affected_edges=(edge.edge_id, seen[key]),
                    severity='low',
                )
            )
        else:
            seen[key] = edge.edge_id
    return violations


def validate_layer_consistency(graph: KnowledgeGraph) -> list[IntegrityViolation]:
    """Check that edges connecting different layers use valid cross-layer relationships."""
    violations: list[IntegrityViolation] = []
    for edge in graph._edges.values():
        src = graph.get_node(edge.source_node)
        tgt = graph.get_node(edge.target_node)
        if src is None or tgt is None:
            continue
        if src.layer != tgt.layer:
            # Cross-layer edges should be one of the "meta" relationships
            valid_cross_layer = {
                RelationshipCategory.DERIVED_FROM,
                RelationshipCategory.SUPPORTS,
                RelationshipCategory.INFLUENCES,
                RelationshipCategory.PART_OF,
                RelationshipCategory.CONTAINS,
            }
            if edge.relationship not in valid_cross_layer:
                violations.append(
                    IntegrityViolation(
                        violation_type='layer_inconsistency',
                        description=(
                            f'Edge {edge.edge_id} connects {src.layer.value} → '
                            f'{tgt.layer.value} with {edge.relationship.value}'
                        ),
                        affected_edges=(edge.edge_id,),
                        severity='low',
                    )
                )
    return violations


def validate_node_uniqueness(graph: KnowledgeGraph) -> list[IntegrityViolation]:
    """Check for duplicate node IDs (should never happen in a dict, but verify)."""
    ids = [n.node_id for n in graph._nodes.values()]
    seen: set[str] = set()
    violations: list[IntegrityViolation] = []
    for nid in ids:
        if nid in seen:
            violations.append(
                IntegrityViolation(
                    violation_type='duplicate_node',
                    description=f'Duplicate node ID: {nid}',
                    affected_nodes=(nid,),
                    severity='critical',
                )
            )
        seen.add(nid)
    return violations


def validate_graph(graph: KnowledgeGraph) -> IntegrityReport:
    """Run all integrity checks and return a report."""
    violations: list[IntegrityViolation] = []
    violations.extend(validate_orphan_edges(graph))
    violations.extend(validate_self_loops(graph))
    violations.extend(validate_duplicate_edges(graph))
    violations.extend(validate_layer_consistency(graph))
    violations.extend(validate_node_uniqueness(graph))

    is_valid = all(v.severity != 'critical' for v in violations)

    return IntegrityReport(
        is_valid=is_valid,
        violations=tuple(violations),
        node_count=graph.node_count,
        edge_count=graph.edge_count,
    )
