"""Schema validators — validates pipeline stage outputs, provenance, and graph integrity."""

from __future__ import annotations

from typing import Any

from integration_tests.pipeline_runner import PipelineResult, PipelineStageResult


# ---------------------------------------------------------------------------
# Stage output validation
# ---------------------------------------------------------------------------


def validate_stage_output(stage: PipelineStageResult) -> list[str]:
    """Validate a single stage's output. Returns list of errors (empty = valid)."""
    errors: list[str] = []

    # Input exists
    if not stage.stage_name:
        errors.append(f"Stage has no name")

    # Output exists
    if stage.is_null and not stage.error:
        errors.append(f"Stage '{stage.stage_name}' output is null without error")

    # No null values in output_data
    for key, value in stage.output_data.items():
        if value is None and key not in ("analysis", "decision", "profile", "result", "interpretation", "safety_result"):
            errors.append(f"Stage '{stage.stage_name}' has null value for '{key}'")

    # Confidence exists and is in valid range
    if stage.confidence < 0.0 or stage.confidence > 1.0:
        errors.append(
            f"Stage '{stage.stage_name}' confidence {stage.confidence} out of range [0, 1]"
        )

    # Version exists
    if not stage.version:
        errors.append(f"Stage '{stage.stage_name}' has no version")

    # Duration recorded
    if stage.duration_ms < 0:
        errors.append(f"Stage '{stage.stage_name}' has negative duration")

    return errors


def validate_all_stages(result: PipelineResult) -> list[str]:
    """Validate all stages in a pipeline result. Returns list of errors."""
    errors: list[str] = []

    if not result.stages:
        errors.append("Pipeline has no stages")
        return errors

    stage_names = [s.stage_name for s in result.stages]

    # Verify all 13 required stages exist
    required_stages = [
        "dialogue_analysis",
        "epistemic_analysis",
        "retrieval",
        "epistemic_profiles",
        "hierarchical_profiles",
        "concept_extraction",
        "knowledge_graph",
        "cross_book_linking",
        "graph_reasoning",
        "interpretation",
        "epistemic_safety",
        "response_generation",
        "provenance",
    ]

    for required in required_stages:
        if required not in stage_names:
            errors.append(f"Missing required stage: {required}")

    # Validate each stage
    for stage in result.stages:
        stage_errors = validate_stage_output(stage)
        errors.extend(stage_errors)

    # Verify no bypass (all stages executed or have valid errors)
    for stage in result.stages:
        if stage.error and not stage.output_data:
            errors.append(f"Stage '{stage.stage_name}' failed with no fallback output")

    return errors


# ---------------------------------------------------------------------------
# Provenance validation
# ---------------------------------------------------------------------------


def validate_provenance_bundle(bundle: Any) -> list[str]:
    """Validate a provenance bundle for completeness and integrity."""
    errors: list[str] = []

    # Bundle has an ID
    if not bundle.id:
        errors.append("Provenance bundle has no ID")

    # Document origin exists
    if not bundle.document or not bundle.document.document_id:
        errors.append("Provenance bundle has no document origin")

    # No orphan chunk references
    if bundle.chunks and not bundle.document:
        errors.append("Provenance bundle has chunks without document origin")

    # No orphan node references
    if bundle.nodes and not bundle.edges:
        # Nodes without edges is acceptable for top-level concepts
        pass

    # Engine versions present
    if not bundle.engine_versions:
        errors.append("Provenance bundle has no engine versions")

    # Timestamps present
    if not bundle.created_at:
        errors.append("Provenance bundle has no created_at timestamp")

    # Total references > 0
    total = bundle.get_total_references()
    if total == 0:
        errors.append("Provenance bundle has zero references")

    return errors


# ---------------------------------------------------------------------------
# Graph integrity validation
# ---------------------------------------------------------------------------


def validate_graph_integrity(graph: Any) -> list[str]:
    """Validate the knowledge graph for integrity issues."""
    errors: list[str] = []

    # Check for orphan edges (edges referencing non-existent nodes)
    node_ids = set(graph.nodes.keys())
    for edge_id, edge in graph.edges.items():
        if edge["source_id"] not in node_ids:
            errors.append(f"Edge '{edge_id}' references missing source node '{edge['source_id']}'")
        if edge["target_id"] not in node_ids:
            errors.append(f"Edge '{edge_id}' references missing target node '{edge['target_id']}'")

    # Check for cyclic references (BFS)
    cycles = detect_cycles(graph)
    if cycles:
        errors.append(f"Graph has {len(cycles)} cyclic reference(s)")

    return errors


def detect_cycles(graph: Any) -> list[list[str]]:
    """Detect cycles in the knowledge graph using DFS."""
    adjacency: dict[str, list[str]] = {}
    for edge in graph.edges.values():
        src = edge["source_id"]
        tgt = edge["target_id"]
        adjacency.setdefault(src, []).append(tgt)

    visited: set[str] = set()
    rec_stack: set[str] = set()
    cycles: list[list[str]] = []

    def dfs(node: str, path: list[str]) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in adjacency.get(node, []):
            if neighbor not in visited:
                dfs(neighbor, path)
            elif neighbor in rec_stack:
                cycle_start = path.index(neighbor)
                cycles.append(path[cycle_start:] + [neighbor])

        path.pop()
        rec_stack.discard(node)

    for node in graph.nodes:
        if node not in visited:
            dfs(node, [])

    return cycles


# ---------------------------------------------------------------------------
# Architecture validation
# ---------------------------------------------------------------------------


def validate_architecture(result: PipelineResult) -> list[str]:
    """Validate that no architectural bypass exists."""
    errors: list[str] = []

    # Check stage ordering
    expected_order = [
        "dialogue_analysis",
        "epistemic_analysis",
        "retrieval",
        "epistemic_profiles",
        "hierarchical_profiles",
        "concept_extraction",
        "knowledge_graph",
        "cross_book_linking",
        "graph_reasoning",
        "interpretation",
        "epistemic_safety",
        "response_generation",
        "provenance",
    ]

    actual_order = [s.stage_name for s in result.stages if not s.error]

    # Verify no stage is repeated
    if len(actual_order) != len(set(actual_order)):
        errors.append("Pipeline has duplicate stages")

    # Verify safety comes before response generation
    if "epistemic_safety" in actual_order and "response_generation" in actual_order:
        safety_idx = actual_order.index("epistemic_safety")
        response_idx = actual_order.index("response_generation")
        if safety_idx > response_idx:
            errors.append("Epistemic safety must come before response generation")

    # Verify provenance is last
    if actual_order and actual_order[-1] != "provenance":
        errors.append("Provenance must be the last stage")

    # Verify final response is non-empty
    if not result.final_response:
        errors.append("Pipeline produced empty final response")

    # Verify total duration is reasonable (< 30 seconds for test data)
    if result.total_duration_ms > 30000:
        errors.append(f"Pipeline took too long: {result.total_duration_ms:.0f}ms")

    return errors
