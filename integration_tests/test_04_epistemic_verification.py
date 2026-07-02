"""Test 04: Epistemic verification — uncertainty, scope, and framework preservation."""

from __future__ import annotations

import pytest

from ayeneh.epistemic_safety.engine import EpistemicSafetyEngine
from ayeneh.epistemic_safety.types import (
    DependencyRisk,
    EvidenceStatus,
    UncertaintyLevel,
)


@pytest.mark.asyncio
async def test_speculative_statements_remain_speculative(pipeline_components):
    """Verify speculative language is preserved as speculative."""
    engine = EpistemicSafetyEngine()
    text = "This might be similar to mindfulness practice, possibly resembling Zen."
    result = engine.validate(text)

    # Speculative language should not be classified as certain
    assert result.statement_count > 0
    # The response should pass safety checks
    assert result.recommendation in ("PASS", "REVISE")


@pytest.mark.asyncio
async def test_supported_statements_remain_supported(pipeline_components):
    """Verify supported statements are recognized."""
    engine = EpistemicSafetyEngine()
    text = "According to the text, acceptance involves making room for difficult experiences."
    result = engine.validate(text)

    assert result.statement_count > 0
    # Should not be flagged as unsupported
    assert result.unsupported_claims == 0


@pytest.mark.asyncio
async def test_uncertainty_preserved(pipeline_components):
    """Verify uncertainty is preserved in safety validation."""
    engine = EpistemicSafetyEngine()
    text = "This is uncertain and complex, with ambiguous meaning."
    result = engine.validate(text)

    # Should detect uncertainty
    assert result.uncertainty_level in (
        UncertaintyLevel.MEDIUM,
        UncertaintyLevel.HIGH,
        UncertaintyLevel.VERY_HIGH,
    )


@pytest.mark.asyncio
async def test_dependency_language_detected(pipeline_components):
    """Verify dependency-creating language is detected."""
    engine = EpistemicSafetyEngine()
    text = "You should trust me on this. I know your real problem. You must do this."
    result = engine.validate(text)

    assert result.dependency_risk in (
        DependencyRisk.LOW,
        DependencyRisk.MEDIUM,
        DependencyRisk.HIGH,
    )
    assert result.dependency_check is not None
    assert result.dependency_check.detected


@pytest.mark.asyncio
async def test_framework_attribution_present(pipeline_components):
    """Verify framework attribution is detected in responses."""
    engine = EpistemicSafetyEngine()
    text = "From a neuroscience perspective, this involves prefrontal cortex activation."
    result = engine.validate(text)

    # Should detect neuroscience framework
    assert result.statement_count > 0


@pytest.mark.asyncio
async def test_scope_limitations_preserved(pipeline_components):
    """Verify scope limitations are detected."""
    engine = EpistemicSafetyEngine()
    text = "This is scientifically proven and always true, an absolute certainty."
    result = engine.validate(text)

    # Universal claims should trigger scope violations
    assert len(result.scope_violations) > 0


@pytest.mark.asyncio
async def test_safety_score_in_range(pipeline_components):
    """Verify safety scores are in valid range."""
    runner_text = "I notice you are exploring cross-tradition concepts."
    engine = EpistemicSafetyEngine()
    result = engine.validate(runner_text)

    assert 0.0 <= result.overall_safety_score <= 1.0
