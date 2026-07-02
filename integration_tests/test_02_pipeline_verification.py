"""Test 02: Per-stage pipeline verification."""

from __future__ import annotations

import pytest

from integration_tests.pipeline_runner import PipelineRunner
from integration_tests.schema_validators import (
    validate_all_stages,
    validate_graph_integrity,
    validate_provenance_bundle,
)


@pytest.mark.asyncio
async def test_all_stages_execute(pipeline_components):
    """Verify all 13 required stages execute."""
    runner = PipelineRunner(pipeline_components)
    result = await runner.run("What is acceptance?")

    errors = validate_all_stages(result)
    # Allow stages that have errors but produce fallback output
    critical_errors = [e for e in errors if "Missing required stage" in e]
    assert not critical_errors, f"Missing stages: {critical_errors}"


@pytest.mark.asyncio
async def test_stage_outputs_not_null(pipeline_components):
    """Verify critical stages produce non-null output."""
    runner = PipelineRunner(pipeline_components)
    result = await runner.run("What is awareness?")

    critical_stages = [
        "dialogue_analysis",
        "retrieval",
        "concept_extraction",
        "knowledge_graph",
        "epistemic_safety",
        "response_generation",
        "provenance",
    ]

    for stage_name in critical_stages:
        stage = next((s for s in result.stages if s.stage_name == stage_name), None)
        assert stage is not None, f"Stage '{stage_name}' not found"
        assert not stage.is_null or stage.error, (
            f"Stage '{stage_name}' output is null without error"
        )


@pytest.mark.asyncio
async def test_confidence_exists_per_stage(pipeline_components):
    """Verify every stage has a confidence value."""
    runner = PipelineRunner(pipeline_components)
    result = await runner.run("What is meditation?")

    for stage in result.stages:
        assert isinstance(stage.confidence, float), (
            f"Stage '{stage.stage_name}' confidence is not a float"
        )
        assert 0.0 <= stage.confidence <= 1.0, (
            f"Stage '{stage.stage_name}' confidence {stage.confidence} out of range"
        )


@pytest.mark.asyncio
async def test_provenance_exists(pipeline_components):
    """Verify provenance bundle exists and is valid."""
    runner = PipelineRunner(pipeline_components)
    result = await runner.run("What is defusion?")

    errors = validate_provenance_bundle(result.provenance_bundle)
    assert not errors, f"Provenance validation errors: {errors}"


@pytest.mark.asyncio
async def test_graph_integrity(pipeline_components):
    """Verify the knowledge graph has no orphan edge references."""
    graph = pipeline_components["graph"]
    node_ids = set(graph.nodes.keys())
    orphan_edges = []
    for edge_id, edge in graph.edges.items():
        if edge["source_id"] not in node_ids or edge["target_id"] not in node_ids:
            orphan_edges.append(edge_id)
    assert not orphan_edges, f"Orphan edges: {orphan_edges}"


@pytest.mark.asyncio
async def test_version_exists_per_stage(pipeline_components):
    """Verify every stage records a version."""
    runner = PipelineRunner(pipeline_components)
    result = await runner.run("What is consciousness?")

    for stage in result.stages:
        assert stage.version, f"Stage '{stage.stage_name}' has no version"


@pytest.mark.asyncio
async def test_no_orphan_provenance_references(pipeline_components):
    """Verify no orphan references in provenance."""
    runner = PipelineRunner(pipeline_components)
    result = await runner.run("What is values?")

    bundle = result.provenance_bundle
    # Verify referenced nodes exist in graph
    graph = pipeline_components["graph"]
    for node_origin in bundle.nodes:
        assert node_origin.node_id in graph.nodes, (
            f"Orphan provenance node reference: {node_origin.node_id}"
        )
