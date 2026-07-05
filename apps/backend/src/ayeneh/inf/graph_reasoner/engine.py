"""INF-02 Graph Reasoning Engine.

Graph-based reasoning over knowledge networks implementing an 8-phase pipeline:
1. Context Collection
2. Starting Node Selection
3. Relationship Expansion
4. Traversal Execution
5. Subgraph Construction
6. Pattern Detection
7. Inference Generation
8. Reality Calibration
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from ayeneh.inf.graph_reasoner.structural import StructuralReasoning
from ayeneh.inf.graph_reasoner.types import (
    TRAVERSAL_STRATEGIES,
    AlternativePath,
    GraphReasoningObject,
    GraphReasoningResult,
    StructuralPattern,
    SubgraphResult,
    TraversalStep,
)

logger = structlog.get_logger(__name__)


class GraphReasoningEngine:
    """Graph-based reasoning engine (INF-02).

    Pipeline:
        1. Context Collection — gather context for graph traversal
        2. Starting Node Selection — identify entry points
        3. Relationship Expansion — discover adjacent relationships
        4. Traversal Execution — traverse the graph
        5. Subgraph Construction — build relevant subgraph
        6. Pattern Detection — find structural patterns
        7. Inference Generation — generate inferences from patterns
        8. Reality Calibration — validate and calibrate results
    """

    def __init__(self) -> None:
        self._reasoning_sessions: dict[str, GraphReasoningObject] = {}
        self._structural = StructuralReasoning()

    def process(
        self,
        context: dict[str, Any],
        graph: dict[str, Any] | None = None,
        starting_nodes: list[str] | None = None,
    ) -> GraphReasoningResult:
        """Run the full INF-02 pipeline.

        Parameters
        ----------
        context:
            Context dict with ``'context_id'``, ``'domain'``, and optional
            ``'query'`` keys.
        graph:
            Graph dict with ``'nodes'`` (list of node dicts) and ``'edges'``
            (list of edge dicts with ``'source'``, ``'target'``, ``'type'``).
        starting_nodes:
            Optional list of node IDs to start traversal from.
        """
        logger.info(
            'inf.graph_reasoner.pipeline_started',
            context_id=context.get('context_id', ''),
            graph_nodes=len((graph or {}).get('nodes', [])),
        )

        graph = graph or {'nodes': [], 'edges': []}

        # Phase 1: Context Collection
        collected = self._phase_context_collection(context, graph)

        # Phase 2: Starting Node Selection
        selected_nodes = self._phase_starting_node_selection(
            collected, starting_nodes,
        )

        # Phase 3: Relationship Expansion
        expanded = self._phase_relationship_expansion(collected, selected_nodes)

        # Phase 4: Traversal Execution
        traversal = self._phase_traversal_execution(
            collected, selected_nodes, expanded,
        )

        # Phase 5: Subgraph Construction
        subgraph = self._phase_subgraph_construction(
            collected, traversal, expanded,
        )

        # Phase 6: Pattern Detection
        patterns = self._phase_pattern_detection(subgraph)

        # Phase 7: Inference Generation
        inferences = self._phase_inference_generation(
            subgraph, patterns, collected,
        )

        # Phase 8: Reality Calibration
        result = self._phase_reality_calibration(
            collected, subgraph, patterns, traversal, inferences,
        )

        logger.info(
            'inf.graph_reasoner.pipeline_completed',
            reasoning_id=result.reasoning_object.reasoning_id,
            pattern_count=len(result.patterns),
            confidence=result.overall_confidence,
        )

        return result

    # ------------------------------------------------------------------
    # Phase 1: Context Collection
    # ------------------------------------------------------------------

    def _phase_context_collection(
        self,
        context: dict[str, Any],
        graph: dict[str, Any],
    ) -> dict[str, Any]:
        """Collect context for graph reasoning."""
        logger.debug('inf.graph_reasoner.phase1_context_collection')

        return {
            'context_id': context.get('context_id', ''),
            'domain': context.get('domain', 'general'),
            'query': context.get('query', ''),
            'graph_nodes': graph.get('nodes', []),
            'graph_edges': graph.get('edges', []),
            'strategy': context.get('traversal_strategy', 'breadth_first'),
        }

    # ------------------------------------------------------------------
    # Phase 2: Starting Node Selection
    # ------------------------------------------------------------------

    def _phase_starting_node_selection(
        self,
        context: dict[str, Any],
        starting_nodes: list[str] | None,
    ) -> list[str]:
        """Select starting nodes for traversal."""
        logger.debug('inf.graph_reasoner.phase2_starting_node_selection')

        if starting_nodes:
            return starting_nodes

        # Auto-select nodes with highest importance
        nodes = context.get('graph_nodes', [])
        if not nodes:
            return []

        scored = []
        for node in nodes:
            node_id = node.get('id', '')
            importance = node.get('importance', 0.5)
            connection_count = sum(
                1 for e in context.get('graph_edges', [])
                if e.get('source') == node_id or e.get('target') == node_id
            )
            score = importance * 0.6 + min(connection_count / 10.0, 1.0) * 0.4
            scored.append((node_id, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [nid for nid, _ in scored[:5]]

    # ------------------------------------------------------------------
    # Phase 3: Relationship Expansion
    # ------------------------------------------------------------------

    def _phase_relationship_expansion(
        self,
        context: dict[str, Any],
        starting_nodes: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        """Expand relationships from starting nodes."""
        logger.debug('inf.graph_reasoner.phase3_relationship_expansion')

        edges = context.get('graph_edges', [])
        adjacency: dict[str, list[dict[str, Any]]] = {}

        for node_id in starting_nodes:
            adjacency[node_id] = []
            for edge in edges:
                if edge.get('source') == node_id or edge.get('target') == node_id:
                    adjacency[node_id].append(edge)

        return adjacency

    # ------------------------------------------------------------------
    # Phase 4: Traversal Execution
    # ------------------------------------------------------------------

    def _phase_traversal_execution(
        self,
        context: dict[str, Any],
        starting_nodes: list[str],
        adjacency: dict[str, list[dict[str, Any]]],
    ) -> tuple[TraversalStep, ...]:
        """Execute graph traversal."""
        logger.debug('inf.graph_reasoner.phase4_traversal_execution')

        strategy = context.get('strategy', 'breadth_first')
        if strategy not in TRAVERSAL_STRATEGIES:
            strategy = 'breadth_first'

        steps: list[TraversalStep] = []
        visited: set[str] = set()
        queue = list(starting_nodes)
        depth = 0
        max_depth = context.get('max_depth', 3)

        while queue and depth <= max_depth:
            next_queue: list[str] = []
            for node_id in queue:
                if node_id in visited:
                    continue
                visited.add(node_id)

                for edge in adjacency.get(node_id, []):
                    target = edge.get('target', '') if edge.get('source') == node_id else edge.get('source', '')
                    if target and target not in visited:
                        steps.append(TraversalStep(
                            step_id=str(uuid.uuid4()),
                            from_node=node_id,
                            to_node=target,
                            relationship_type=edge.get('type', 'related'),
                            weight=edge.get('weight', 0.5),
                            depth=depth,
                        ))
                        next_queue.append(target)

            queue = next_queue
            depth += 1

        return tuple(steps)

    # ------------------------------------------------------------------
    # Phase 5: Subgraph Construction
    # ------------------------------------------------------------------

    def _phase_subgraph_construction(
        self,
        context: dict[str, Any],
        traversal: tuple[TraversalStep, ...],
        adjacency: dict[str, list[dict[str, Any]]],
    ) -> SubgraphResult:
        """Construct subgraph from traversal results."""
        logger.debug('inf.graph_reasoner.phase5_subgraph_construction')

        visited_nodes: set[str] = set()
        for step in traversal:
            visited_nodes.add(step.from_node)
            visited_nodes.add(step.to_node)

        node_dicts = [
            n for n in context.get('graph_nodes', [])
            if n.get('id') in visited_nodes
        ]
        edge_dicts = [
            e for e in context.get('graph_edges', [])
            if e.get('source') in visited_nodes or e.get('target') in visited_nodes
        ]

        max_depth = max((s.depth for s in traversal), default=0)

        return SubgraphResult(
            nodes=tuple(node_dicts),
            edges=tuple(edge_dicts),
            root_node=context.get('graph_nodes', [{}])[0].get('id', '') if context.get('graph_nodes') else '',
            depth=max_depth,
            node_count=len(node_dicts),
            edge_count=len(edge_dicts),
        )

    # ------------------------------------------------------------------
    # Phase 6: Pattern Detection
    # ------------------------------------------------------------------

    def _phase_pattern_detection(
        self,
        subgraph: SubgraphResult,
    ) -> tuple[StructuralPattern, ...]:
        """Detect structural patterns in the subgraph."""
        logger.debug('inf.graph_reasoner.phase6_pattern_detection')

        return self._structural.detect_patterns(
            nodes=[dict(n) for n in subgraph.nodes],
            edges=[dict(e) for e in subgraph.edges],
        )

    # ------------------------------------------------------------------
    # Phase 7: Inference Generation
    # ------------------------------------------------------------------

    def _phase_inference_generation(
        self,
        subgraph: SubgraphResult,
        patterns: tuple[StructuralPattern, ...],
        context: dict[str, Any],
    ) -> tuple[dict[str, Any], ...]:
        """Generate inferences from graph patterns."""
        logger.debug('inf.graph_reasoner.phase7_inference_generation')

        inferences: list[dict[str, Any]] = []
        for pattern in patterns:
            inferences.append({
                'inference_id': str(uuid.uuid4()),
                'type': 'graph_structural',
                'pattern_type': pattern.pattern_type,
                'statement': pattern.description,
                'confidence': pattern.confidence,
                'evidence_count': pattern.evidence_count,
                'node_ids': pattern.node_ids,
            })

        # Add general subgraph inferences
        if subgraph.node_count > 5:
            inferences.append({
                'inference_id': str(uuid.uuid4()),
                'type': 'graph_density',
                'pattern_type': 'high_density',
                'statement': f'Subgraph contains {subgraph.node_count} nodes with {subgraph.edge_count} edges',
                'confidence': 0.6,
                'evidence_count': subgraph.edge_count,
                'node_ids': (),
            })

        return tuple(inferences)

    # ------------------------------------------------------------------
    # Phase 8: Reality Calibration
    # ------------------------------------------------------------------

    def _phase_reality_calibration(
        self,
        context: dict[str, Any],
        subgraph: SubgraphResult,
        patterns: tuple[StructuralPattern, ...],
        traversal: tuple[TraversalStep, ...],
        inferences: tuple[dict[str, Any], ...],
    ) -> GraphReasoningResult:
        """Calibrate and finalize results."""
        logger.debug('inf.graph_reasoner.phase8_reality_calibration')

        reasoning_id = str(uuid.uuid4())

        # Calculate overall confidence
        pattern_confs = [p.confidence for p in patterns]
        inf_confs = [i.get('confidence', 0.0) for i in inferences]
        all_confs = pattern_confs + inf_confs
        overall = sum(all_confs) / len(all_confs) if all_confs else 0.0

        # Find alternative paths
        alt_paths = self._find_alternative_paths(context, traversal)

        # Calibration notes
        notes: list[str] = []
        if subgraph.node_count == 0:
            notes.append('Empty subgraph — no graph relationships found')
        if len(patterns) == 0:
            notes.append('No structural patterns detected')
        if overall > 0.8:
            notes.append('High confidence — multiple supporting patterns')

        reasoning_obj = GraphReasoningObject(
            reasoning_id=reasoning_id,
            starting_nodes=tuple(
                context.get('graph_nodes', [{}])[0].get('id', '')
                if context.get('graph_nodes') else ''
            ) if context.get('graph_nodes') else (),
            traversal_strategy=context.get('strategy', 'breadth_first'),
            visited_nodes=tuple(
                n for step in traversal for n in (step.from_node, step.to_node)
            ),
            visited_relationships=tuple(
                step.relationship_type for step in traversal
            ),
            generated_subgraph={
                'node_count': subgraph.node_count,
                'edge_count': subgraph.edge_count,
                'depth': subgraph.depth,
            },
            detected_patterns=tuple(
                {'type': p.pattern_type, 'confidence': p.confidence}
                for p in patterns
            ),
            reasoning_confidence=round(overall, 4),
            traversal_depth=subgraph.depth,
            alternative_paths=tuple(
                {'path_id': ap.path_id, 'confidence': ap.confidence}
                for ap in alt_paths
            ),
        )

        self._reasoning_sessions[reasoning_id] = reasoning_obj

        return GraphReasoningResult(
            reasoning_object=reasoning_obj,
            subgraph=subgraph,
            patterns=patterns,
            traversals=traversal,
            alternative_paths=tuple(alt_paths),
            inferences=inferences,
            calibration_notes=tuple(notes),
            overall_confidence=round(overall, 4),
            processing_metadata={
                'node_count': subgraph.node_count,
                'edge_count': subgraph.edge_count,
                'pattern_count': len(patterns),
                'inference_count': len(inferences),
                'traversal_steps': len(traversal),
            },
        )

    def _find_alternative_paths(
        self,
        context: dict[str, Any],
        traversal: tuple[TraversalStep, ...],
    ) -> list[AlternativePath]:
        """Find alternative reasoning paths."""
        alternatives: list[AlternativePath] = []

        # Simple: if there are multiple edges from any node, those are alternatives
        edges = context.get('graph_edges', [])
        visited_nodes = {s.from_node for s in traversal}

        for node_id in visited_nodes:
            outgoing = [
                e for e in edges
                if e.get('source') == node_id and e.get('target') not in visited_nodes
            ]
            if len(outgoing) > 1:
                for edge in outgoing[1:]:
                    alternatives.append(AlternativePath(
                        path_id=str(uuid.uuid4()),
                        nodes=(node_id, edge.get('target', '')),
                        confidence=edge.get('weight', 0.5),
                        explanation=f"Alternative path from {node_id}",
                        length=1,
                    ))

        return alternatives

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_reasoning_session(
        self, reasoning_id: str,
    ) -> GraphReasoningObject | None:
        """Retrieve a reasoning session by ID."""
        return self._reasoning_sessions.get(reasoning_id)

    def get_all_sessions(self) -> list[GraphReasoningObject]:
        """Retrieve all reasoning sessions."""
        return list(self._reasoning_sessions.values())
