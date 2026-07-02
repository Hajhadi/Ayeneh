"""Test 01: Complete pipeline user journeys."""

from __future__ import annotations

import pytest

from integration_tests.pipeline_runner import PipelineRunner


@pytest.mark.asyncio
async def test_full_pipeline_simple_question(pipeline_components):
    """Run a simple question through the entire pipeline."""
    runner = PipelineRunner(pipeline_components)
    result = await runner.run("What is awareness?")

    assert result.final_response, "Pipeline produced no response"
    assert len(result.stages) == 13, f"Expected 13 stages, got {len(result.stages)}"
    assert not result.errors, f"Pipeline errors: {result.errors}"


@pytest.mark.asyncio
async def test_full_pipeline_cross_tradition_question(pipeline_components):
    """Run a cross-tradition question through the pipeline."""
    runner = PipelineRunner(pipeline_components)
    result = await runner.run(
        "What is the relationship between ACT acceptance and Buddhist non-attachment?"
    )

    assert result.final_response, "Pipeline produced no response"
    assert len(result.stages) == 13
    assert not result.errors


@pytest.mark.asyncio
async def test_full_pipeline_comparative_question(pipeline_components):
    """Run a comparative question through the pipeline."""
    runner = PipelineRunner(pipeline_components)
    result = await runner.run(
        "Compare Sapolsky's stress model with ACT."
    )

    assert result.final_response, "Pipeline produced no response"
    assert len(result.stages) == 13
    assert not result.errors


@pytest.mark.asyncio
async def test_pipeline_produces_provenance(pipeline_components):
    """Verify the pipeline produces a provenance bundle."""
    runner = PipelineRunner(pipeline_components)
    result = await runner.run("What is mindfulness?")

    bundle = result.provenance_bundle
    assert bundle.id, "Provenance bundle has no ID"
    assert bundle.document, "Provenance bundle has no document"
    assert bundle.engine_versions, "Provenance bundle has no engine versions"
    assert bundle.get_total_references() > 0, "Provenance bundle has zero references"


@pytest.mark.asyncio
async def test_pipeline_confidence_in_range(pipeline_components):
    """Verify all stage confidences are in [0, 1]."""
    runner = PipelineRunner(pipeline_components)
    result = await runner.run("What is consciousness?")

    for stage in result.stages:
        assert 0.0 <= stage.confidence <= 1.0, (
            f"Stage '{stage.stage_name}' confidence {stage.confidence} out of range"
        )


@pytest.mark.asyncio
async def test_pipeline_stages_have_timing(pipeline_components):
    """Verify all stages record timing."""
    runner = PipelineRunner(pipeline_components)
    result = await runner.run("What is suffering?")

    for stage in result.stages:
        assert stage.duration_ms >= 0, (
            f"Stage '{stage.stage_name}' has negative duration"
        )


@pytest.mark.asyncio
async def test_pipeline_total_duration_reasonable(pipeline_components):
    """Verify total pipeline duration is reasonable."""
    runner = PipelineRunner(pipeline_components)
    result = await runner.run("What is Zen?")

    assert result.total_duration_ms > 0, "Pipeline duration not recorded"
    assert result.total_duration_ms < 30000, (
        f"Pipeline took too long: {result.total_duration_ms:.0f}ms"
    )
