"""Tests for the INF-01 Inference Engine."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime

from ayeneh.inf.inference.types import (
    INFERENCE_TYPES,
    EVIDENCE_STANDARDS,
    CompetingHypothesis,
    ContradictionRecord,
    EvidenceQualityAssessment,
    InferenceObject,
    InferenceResult,
    ReasoningStep,
)
from ayeneh.inf.inference.engine import InferenceEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    return InferenceEngine()


@pytest.fixture
def sample_context():
    return {
        'context_id': 'test-ctx-1',
        'domain': 'general',
        'query': 'What patterns exist?',
    }


@pytest.fixture
def sample_memories():
    return [
        {
            'id': 'mem-1',
            'content': 'User mentioned daily coffee habit',
            'source': 'conversation',
            'confidence': 0.8,
            'category': 'behavior',
        },
        {
            'id': 'mem-2',
            'content': 'User reports feeling productive after coffee',
            'source': 'conversation',
            'confidence': 0.7,
            'category': 'observation',
        },
        {
            'id': 'mem-3',
            'content': 'User values morning routines',
            'source': 'conversation',
            'confidence': 0.6,
            'category': 'statement',
        },
    ]


# ---------------------------------------------------------------------------
# Type tests
# ---------------------------------------------------------------------------


class TestInferenceTypes:
    """Tests for INF-01 type definitions."""

    def test_inference_types_count(self):
        assert len(INFERENCE_TYPES) == 10

    def test_evidence_standards_cover_all_types(self):
        for inf_type in INFERENCE_TYPES:
            assert inf_type in EVIDENCE_STANDARDS

    def test_inference_object_creation(self):
        obj = InferenceObject(
            inference_id='inf-1',
            context_id='ctx-1',
            inference_type='behavioral',
            statement='Test statement',
        )
        assert obj.inference_id == 'inf-1'
        assert obj.inference_type == 'behavioral'
        assert obj.confidence == 0.0
        assert obj.creation_timestamp is not None

    def test_inference_object_frozen(self):
        obj = InferenceObject(
            inference_id='inf-1',
            context_id='ctx-1',
            inference_type='behavioral',
            statement='Test',
        )
        with pytest.raises(AttributeError):
            obj.statement = 'Changed'  # type: ignore[misc]

    def test_inference_result_defaults(self):
        result = InferenceResult()
        assert result.inferences == ()
        assert result.overall_confidence == 0.0

    def test_evidence_quality_assessment(self):
        qa = EvidenceQualityAssessment(
            directness=0.8,
            specificity=0.7,
            temporal_proximity=0.6,
            consistency=0.9,
            source_reliability=0.75,
        )
        overall = qa.overall()
        assert 0.0 <= overall <= 1.0
        assert overall > 0.5

    def test_reasoning_step_creation(self):
        step = ReasoningStep(
            step_id='step-1',
            description='Test step',
            confidence=0.8,
        )
        assert step.step_id == 'step-1'
        assert step.confidence == 0.8

    def test_competing_hypothesis_creation(self):
        hyp = CompetingHypothesis(
            hypothesis_id='hyp-1',
            statement='Alternative hypothesis',
            confidence=0.6,
        )
        assert hyp.hypothesis_id == 'hyp-1'
        assert hyp.confidence == 0.6

    def test_contradiction_record_creation(self):
        contra = ContradictionRecord(
            contradiction_id='contra-1',
            inference_id_a='inf-a',
            inference_id_b='inf-b',
            description='Test contradiction',
            severity=0.7,
        )
        assert contra.severity == 0.7


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestInferenceEngine:
    """Tests for the INF-01 InferenceEngine."""

    def test_engine_initialization(self):
        engine = InferenceEngine()
        assert engine._inferences == {}

    def test_engine_with_ai_router(self):
        router = {'provider': 'test'}
        engine = InferenceEngine(ai_router=router)
        assert engine._ai_router == router

    def test_process_empty_inputs(self, engine, sample_context):
        result = engine.process(sample_context, [])
        assert isinstance(result, InferenceResult)
        assert result.inferences == ()

    def test_process_basic(self, engine, sample_context, sample_memories):
        result = engine.process(sample_context, sample_memories)
        assert isinstance(result, InferenceResult)
        assert len(result.inferences) > 0

    def test_process_produces_inferences(self, engine, sample_context, sample_memories):
        result = engine.process(sample_context, sample_memories)
        for inf in result.inferences:
            assert isinstance(inf, InferenceObject)
            assert inf.inference_type in INFERENCE_TYPES
            assert inf.statement != ''

    def test_process_confidence_range(self, engine, sample_context, sample_memories):
        result = engine.process(sample_context, sample_memories)
        for inf in result.inferences:
            assert 0.0 <= inf.confidence <= 1.0

    def test_process_with_graph(self, engine, sample_context, sample_memories):
        graph = {'nodes': [], 'edges': []}
        result = engine.process(sample_context, sample_memories, graph=graph)
        assert isinstance(result, InferenceResult)

    def test_process_causal_domain(self, engine, sample_memories):
        context = {
            'context_id': 'test-causal',
            'domain': 'causal',
            'query': 'What causes what?',
        }
        result = engine.process(context, sample_memories)
        assert isinstance(result, InferenceResult)

    def test_process_identity_domain(self, engine):
        memories = [
            {
                'id': 'id-1',
                'content': 'Core identity value',
                'confidence': 0.9,
                'category': 'identity',
            },
        ]
        context = {
            'context_id': 'test-identity',
            'domain': 'identity',
        }
        result = engine.process(context, memories)
        assert isinstance(result, InferenceResult)

    def test_get_inference(self, engine, sample_context, sample_memories):
        result = engine.process(sample_context, sample_memories)
        if result.inferences:
            first_id = result.inferences[0].inference_id
            retrieved = engine.get_inference(first_id)
            assert retrieved is not None
            assert retrieved.inference_id == first_id

    def test_get_inference_not_found(self, engine):
        assert engine.get_inference('nonexistent') is None

    def test_get_all_inferences(self, engine, sample_context, sample_memories):
        engine.process(sample_context, sample_memories)
        all_infs = engine.get_all_inferences()
        assert isinstance(all_infs, list)

    def test_reasoning_steps_generated(self, engine, sample_context, sample_memories):
        result = engine.process(sample_context, sample_memories)
        assert len(result.reasoning_steps) == len(result.inferences)

    def test_calibration_notes(self, engine, sample_context, sample_memories):
        result = engine.process(sample_context, sample_memories)
        assert isinstance(result.calibration_notes, tuple)

    def test_processing_metadata(self, engine, sample_context, sample_memories):
        result = engine.process(sample_context, sample_memories)
        assert 'evidence_count' in result.processing_metadata
        assert 'inference_count' in result.processing_metadata

    def test_overall_confidence_calculation(self, engine, sample_context, sample_memories):
        result = engine.process(sample_context, sample_memories)
        assert 0.0 <= result.overall_confidence <= 1.0

    def test_evidence_quality_assessment(self, engine, sample_context, sample_memories):
        result = engine.process(sample_context, sample_memories)
        assert isinstance(result.evidence_assessment, EvidenceQualityAssessment)

    def test_multiple_contexts(self, engine, sample_memories):
        results = []
        for domain in ['behavioral', 'causal', 'identity']:
            context = {'context_id': f'test-{domain}', 'domain': domain}
            result = engine.process(context, sample_memories)
            results.append(result)

        assert all(isinstance(r, InferenceResult) for r in results)

    def test_competing_hypotheses(self, engine, sample_context, sample_memories):
        result = engine.process(sample_context, sample_memories)
        assert isinstance(result.competing_hypotheses, tuple)

    def test_contradictions(self, engine, sample_context, sample_memories):
        result = engine.process(sample_context, sample_memories)
        assert isinstance(result.contradictions, tuple)
