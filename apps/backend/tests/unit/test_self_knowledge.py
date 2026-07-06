"""Tests for SELF-03 Self-Knowledge Engine."""

from __future__ import annotations

import time

import pytest

from ayeneh.self_arch.self_knowledge.engine import SelfKnowledgeEngine
from ayeneh.self_arch.self_knowledge.types import (
    EPISTEMIC_STATUSES,
    KNOWLEDGE_CATEGORIES,
    EvidenceSource,
    ExplainabilityMetadata,
    KnowledgeConfidence,
    KnowledgeException,
    KnowledgeIdentifier,
    KnowledgeRevision,
    SelfKnowledgeObject,
    VerificationResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine() -> SelfKnowledgeEngine:
    return SelfKnowledgeEngine()


# ---------------------------------------------------------------------------
# Type construction tests
# ---------------------------------------------------------------------------


class TestSelfKnowledgeTypes:
    def test_knowledge_identifier_defaults(self) -> None:
        ident = KnowledgeIdentifier()
        assert ident.id == 'knowledge_001'
        assert ident.version == 1
        assert ident.created_at is not None

    def test_evidence_source_defaults(self) -> None:
        es = EvidenceSource()
        assert es.source_type == ''
        assert es.reliability == 0.0

    def test_verification_result_defaults(self) -> None:
        vr = VerificationResult()
        assert vr.is_verified is False
        assert vr.confidence == 0.0
        assert vr.evidence_count == 0

    def test_knowledge_exception_defaults(self) -> None:
        ke = KnowledgeException()
        assert ke.exception_description == ''
        assert ke.severity == 'low'
        assert ke.is_active is True

    def test_knowledge_revision_defaults(self) -> None:
        kr = KnowledgeRevision()
        assert kr.version == ''
        assert kr.change_description == ''
        assert kr.confidence_before == 0.0

    def test_knowledge_confidence_defaults(self) -> None:
        kc = KnowledgeConfidence()
        assert kc.evidence_confidence == 0.0
        assert kc.overall == 0.0

    def test_explainability_metadata_defaults(self) -> None:
        em = ExplainabilityMetadata()
        assert em.reasoning_chain == ()
        assert em.is_explainable is True

    def test_knowledge_categories(self) -> None:
        assert 'verified_capabilities' in KNOWLEDGE_CATEGORIES
        assert 'verified_limitations' in KNOWLEDGE_CATEGORIES
        assert 'operational_characteristics' in KNOWLEDGE_CATEGORIES
        assert 'behavioral_tendencies' in KNOWLEDGE_CATEGORIES
        assert 'performance_statistics' in KNOWLEDGE_CATEGORIES
        assert 'architectural_assumptions' in KNOWLEDGE_CATEGORIES
        assert 'open_questions' in KNOWLEDGE_CATEGORIES
        assert 'experimental_knowledge' in KNOWLEDGE_CATEGORIES
        assert len(KNOWLEDGE_CATEGORIES) == 8

    def test_epistemic_statuses(self) -> None:
        assert 'verified' in EPISTEMIC_STATUSES
        assert 'strongly_supported' in EPISTEMIC_STATUSES
        assert 'provisionally_supported' in EPISTEMIC_STATUSES
        assert 'hypothetical' in EPISTEMIC_STATUSES
        assert 'unknown' in EPISTEMIC_STATUSES
        assert 'refuted' in EPISTEMIC_STATUSES
        assert len(EPISTEMIC_STATUSES) == 6

    def test_self_knowledge_object_defaults(self) -> None:
        obj = SelfKnowledgeObject()
        assert obj.knowledge_id == ''
        assert obj.statement == ''
        assert obj.evidence_sources == ()
        assert obj.confidence == 0.0
        assert obj.verification_status == 'unknown'
        assert obj.associated_modules == ()
        assert obj.revision_history == ()
        assert obj.known_exceptions == ()
        assert obj.applicable_contexts == ()
        assert obj.future_validation_targets == ()
        assert obj.creation_timestamp is not None
        assert obj.explainability_metadata == {}

    def test_self_knowledge_object_frozen(self) -> None:
        obj = SelfKnowledgeObject()
        with pytest.raises(AttributeError):
            obj.confidence = 1.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Engine pipeline tests
# ---------------------------------------------------------------------------


class TestSelfKnowledgeEnginePipeline:
    def test_build_returns_tuple(self, engine: SelfKnowledgeEngine) -> None:
        result = engine.build()
        assert isinstance(result, tuple)

    def test_build_returns_knowledge_objects(self, engine: SelfKnowledgeEngine) -> None:
        result = engine.build()
        assert len(result) > 0
        for entry in result:
            assert isinstance(entry, SelfKnowledgeObject)

    def test_build_populates_knowledge_id(self, engine: SelfKnowledgeEngine) -> None:
        result = engine.build()
        for entry in result:
            assert entry.knowledge_id != ''

    def test_build_populates_statements(self, engine: SelfKnowledgeEngine) -> None:
        result = engine.build()
        statements = [e.statement for e in result]
        assert any('pipeline' in s for s in statements)

    def test_build_populates_evidence_sources(self, engine: SelfKnowledgeEngine) -> None:
        result = engine.build()
        has_evidence = any(len(e.evidence_sources) > 0 for e in result)
        assert has_evidence

    def test_build_populates_positive_confidence(self, engine: SelfKnowledgeEngine) -> None:
        result = engine.build()
        for entry in result:
            assert entry.confidence > 0.0

    def test_build_populates_verification_status(self, engine: SelfKnowledgeEngine) -> None:
        result = engine.build()
        for entry in result:
            assert entry.verification_status != ''

    def test_build_populates_applicable_contexts(self, engine: SelfKnowledgeEngine) -> None:
        result = engine.build()
        has_contexts = any(len(e.applicable_contexts) > 0 for e in result)
        assert has_contexts

    def test_build_populates_validation_targets(self, engine: SelfKnowledgeEngine) -> None:
        result = engine.build()
        has_targets = any(len(e.future_validation_targets) > 0 for e in result)
        assert has_targets

    def test_build_output_is_frozen(self, engine: SelfKnowledgeEngine) -> None:
        result = engine.build()
        for entry in result:
            with pytest.raises(AttributeError):
                entry.confidence = 1.0  # type: ignore[misc]

    def test_build_with_operational_data(self, engine: SelfKnowledgeEngine) -> None:
        op_data = {
            'module_status': {'dlg': 'active', 'inf': 'active'},
            'error_count': 2,
            'response_times': 0.5,
        }
        result = engine.build(operational_data=op_data)
        assert len(result) > 0

    def test_build_with_self_model_data(self, engine: SelfKnowledgeEngine) -> None:
        model_data = {
            'capabilities': ['dialogue_management', 'inference'],
            'limitations': ['context_window'],
        }
        result = engine.build(self_model_data=model_data)
        assert len(result) > 0

    def test_build_with_both_data_sources(self, engine: SelfKnowledgeEngine) -> None:
        op_data = {'module_status': {'dlg': 'active'}}
        model_data = {'capabilities': ['dialogue_management']}
        result = engine.build(operational_data=op_data, self_model_data=model_data)
        assert len(result) > 0

    def test_knowledge_count_property(self, engine: SelfKnowledgeEngine) -> None:
        assert engine.knowledge_count == 0
        engine.build()
        assert engine.knowledge_count > 0

    def test_knowledge_entries_property(self, engine: SelfKnowledgeEngine) -> None:
        assert engine.knowledge_entries == []
        engine.build()
        assert len(engine.knowledge_entries) > 0

    def test_build_multiple_times(self, engine: SelfKnowledgeEngine) -> None:
        engine.build()
        result = engine.build()
        assert len(result) > 0

    def test_build_with_existing_knowledge(self, engine: SelfKnowledgeEngine) -> None:
        engine.build()
        existing = tuple(engine.knowledge_entries)
        result = engine.build(existing_knowledge=existing)
        assert len(result) >= len(existing)

    def test_build_preserves_epistemic_statuses(self, engine: SelfKnowledgeEngine) -> None:
        result = engine.build()
        statuses = {e.verification_status for e in result}
        # At least one status from the default set should be present
        assert statuses & set(EPISTEMIC_STATUSES)


# ---------------------------------------------------------------------------
# Performance tests
# ---------------------------------------------------------------------------


class TestSelfKnowledgePerformance:
    def test_single_build_latency(self, engine: SelfKnowledgeEngine) -> None:
        start = time.monotonic()
        engine.build()
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 100

    def test_multiple_builds_latency(self, engine: SelfKnowledgeEngine) -> None:
        start = time.monotonic()
        for _ in range(10):
            engine.build()
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 500
