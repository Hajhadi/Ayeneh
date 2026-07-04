"""Tests for Decomposed Confidence per SPEC-01A Law 8."""

import pytest
from ayeneh.runtime.pipeline import DecomposedConfidence, PipelineStageResult


class TestDecomposedConfidence:
    def test_creation(self):
        c = DecomposedConfidence(overall=0.8)
        assert c.overall == 0.8
        assert c.retrieval == 0.0

    def test_from_scalar(self):
        c = DecomposedConfidence.from_scalar(0.7, source="test_stage")
        assert c.overall == 0.7
        assert c.source == "test_stage"

    def test_all_components(self):
        c = DecomposedConfidence(
            overall=0.85,
            retrieval=0.9,
            reasoning=0.8,
            evidence=0.7,
            interpretation=0.9,
            safety=1.0,
            provider=0.6,
        )
        assert c.overall == 0.85
        assert c.retrieval == 0.9
        assert c.reasoning == 0.8
        assert c.evidence == 0.7
        assert c.interpretation == 0.9
        assert c.safety == 1.0
        assert c.provider == 0.6


class TestPipelineStageResultDecomposed:
    def test_has_decomposed_confidence(self):
        r = PipelineStageResult(stage_name="test")
        assert isinstance(r.decomposed_confidence, DecomposedConfidence)

    def test_scalar_backward_compat(self):
        r = PipelineStageResult(stage_name="test", confidence=0.75)
        assert r.confidence == 0.75

    def test_decomposed_independently(self):
        r = PipelineStageResult(
            stage_name="test",
            confidence=0.8,
            decomposed_confidence=DecomposedConfidence(
                overall=0.8,
                retrieval=0.9,
                reasoning=0.7,
            ),
        )
        assert r.confidence == 0.8
        assert r.decomposed_confidence.overall == 0.8
        assert r.decomposed_confidence.retrieval == 0.9
