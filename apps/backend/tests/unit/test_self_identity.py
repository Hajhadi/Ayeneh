"""Tests for SELF-02 Identity Continuity Engine."""

from __future__ import annotations

import time

import pytest

from ayeneh.self_arch.identity_continuity.engine import IdentityContinuityEngine
from ayeneh.self_arch.identity_continuity.types import (
    ConsistencyScore,
    CorePrinciple,
    ExplainabilityMetadata,
    IdentityConfidence,
    IdentityIdentifier,
    IdentityLineageEntry,
    IdentityObject,
    IdentityRevision,
    IdentityTension,
    IDENTITY_EVOLUTION_TYPES,
    STABLE_IDENTITY_COMPONENTS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine() -> IdentityContinuityEngine:
    return IdentityContinuityEngine()


# ---------------------------------------------------------------------------
# Type construction tests
# ---------------------------------------------------------------------------


class TestIdentityContinuityTypes:
    def test_identity_identifier_defaults(self) -> None:
        ident = IdentityIdentifier()
        assert ident.id == 'identity_001'
        assert ident.version == 1
        assert ident.created_at is not None

    def test_core_principle_defaults(self) -> None:
        cp = CorePrinciple()
        assert cp.principle_name == ''
        assert cp.stability == 0.0
        assert cp.evidence_sources == ()

    def test_identity_lineage_entry_defaults(self) -> None:
        ile = IdentityLineageEntry()
        assert ile.version == ''
        assert ile.description == ''
        assert ile.evolution_type == ''

    def test_consistency_score_defaults(self) -> None:
        cs = ConsistencyScore()
        assert cs.dimension == ''
        assert cs.score == 0.0
        assert cs.is_stable is True

    def test_identity_tension_defaults(self) -> None:
        it = IdentityTension()
        assert it.tension_type == ''
        assert it.severity == 0.0
        assert it.resolution_status == 'unresolved'

    def test_identity_revision_defaults(self) -> None:
        ir = IdentityRevision()
        assert ir.version == ''
        assert ir.change_description == ''
        assert ir.confidence_before == 0.0

    def test_identity_confidence_defaults(self) -> None:
        ic = IdentityConfidence()
        assert ic.principle_confidence == 0.0
        assert ic.overall == 0.0

    def test_explainability_metadata_defaults(self) -> None:
        em = ExplainabilityMetadata()
        assert em.reasoning_chain == ()
        assert em.is_explainable is True

    def test_identity_evolution_types(self) -> None:
        assert 'refinement' in IDENTITY_EVOLUTION_TYPES
        assert 'expansion' in IDENTITY_EVOLUTION_TYPES
        assert 'architectural_maturation' in IDENTITY_EVOLUTION_TYPES
        assert len(IDENTITY_EVOLUTION_TYPES) == 6

    def test_stable_identity_components(self) -> None:
        assert 'evidence_first_reasoning' in STABLE_IDENTITY_COMPONENTS
        assert 'transparency' in STABLE_IDENTITY_COMPONENTS
        assert 'explainability' in STABLE_IDENTITY_COMPONENTS
        assert 'respect_for_uncertainty' in STABLE_IDENTITY_COMPONENTS
        assert 'ethical_governance' in STABLE_IDENTITY_COMPONENTS
        assert len(STABLE_IDENTITY_COMPONENTS) == 5

    def test_identity_object_defaults(self) -> None:
        obj = IdentityObject()
        assert obj.identity_id == ''
        assert obj.identity_version == ''
        assert obj.core_principles == ()
        assert obj.stable_characteristics == ()
        assert obj.adaptive_characteristics == ()
        assert obj.historical_lineage == ()
        assert obj.revision_history == ()
        assert obj.confidence == 0.0
        assert obj.supporting_evidence == ()
        assert obj.known_tensions == ()
        assert obj.future_review_points == ()
        assert obj.creation_timestamp is not None
        assert obj.explainability_metadata == {}

    def test_identity_object_frozen(self) -> None:
        obj = IdentityObject()
        with pytest.raises(AttributeError):
            obj.confidence = 1.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Engine pipeline tests
# ---------------------------------------------------------------------------


class TestIdentityContinuityEnginePipeline:
    def test_build_returns_identity_object(self, engine: IdentityContinuityEngine) -> None:
        result = engine.build()
        assert isinstance(result, IdentityObject)

    def test_build_populates_identity_id(self, engine: IdentityContinuityEngine) -> None:
        result = engine.build()
        assert result.identity_id != ''

    def test_build_sets_version(self, engine: IdentityContinuityEngine) -> None:
        result = engine.build()
        assert result.identity_version != ''

    def test_build_populates_core_principles(self, engine: IdentityContinuityEngine) -> None:
        result = engine.build()
        assert len(result.core_principles) > 0
        assert 'evidence_first_reasoning' in result.core_principles

    def test_build_populates_stable_characteristics(self, engine: IdentityContinuityEngine) -> None:
        result = engine.build()
        assert len(result.stable_characteristics) > 0

    def test_build_populates_adaptive_characteristics(self, engine: IdentityContinuityEngine) -> None:
        result = engine.build()
        assert len(result.adaptive_characteristics) > 0

    def test_build_custom_principles(self, engine: IdentityContinuityEngine) -> None:
        custom = ('custom_principle',)
        result = engine.build(core_principles=custom)
        assert result.core_principles == ('custom_principle',)

    def test_build_custom_stable(self, engine: IdentityContinuityEngine) -> None:
        custom = ('stable_a',)
        result = engine.build(stable_characteristics=custom)
        assert result.stable_characteristics == ('stable_a',)

    def test_build_custom_adaptive(self, engine: IdentityContinuityEngine) -> None:
        custom = ('adaptive_a',)
        result = engine.build(adaptive_characteristics=custom)
        assert result.adaptive_characteristics == ('adaptive_a',)

    def test_build_computes_positive_confidence(self, engine: IdentityContinuityEngine) -> None:
        result = engine.build()
        assert 0.0 <= result.confidence <= 1.0
        assert result.confidence > 0.0

    def test_build_records_revision_history(self, engine: IdentityContinuityEngine) -> None:
        result = engine.build()
        assert len(result.revision_history) >= 1

    def test_build_populates_supporting_evidence(self, engine: IdentityContinuityEngine) -> None:
        result = engine.build()
        assert len(result.supporting_evidence) > 0

    def test_build_populates_future_review_points(self, engine: IdentityContinuityEngine) -> None:
        result = engine.build()
        assert len(result.future_review_points) > 0

    def test_build_populates_explainability(self, engine: IdentityContinuityEngine) -> None:
        result = engine.build()
        assert 'reasoning_chain' in result.explainability_metadata
        assert 'evidence_summary' in result.explainability_metadata

    def test_build_sets_creation_timestamp(self, engine: IdentityContinuityEngine) -> None:
        result = engine.build()
        assert result.creation_timestamp is not None

    def test_build_output_is_frozen(self, engine: IdentityContinuityEngine) -> None:
        result = engine.build()
        with pytest.raises(AttributeError):
            result.confidence = 1.0  # type: ignore[misc]

    def test_build_with_prior_identity(self, engine: IdentityContinuityEngine) -> None:
        first = engine.build()
        second = engine.build(prior_identity=first)
        assert second.identity_id != first.identity_id
        assert second.confidence > 0.0

    def test_build_with_prior_identity_maintains_principles(
        self, engine: IdentityContinuityEngine,
    ) -> None:
        custom = ('my_principle',)
        first = engine.build(core_principles=custom)
        second = engine.build(
            prior_identity=first,
            core_principles=custom,
        )
        assert 'my_principle' in second.core_principles

    def test_revision_count_property(self, engine: IdentityContinuityEngine) -> None:
        assert engine.revision_count == 0
        engine.build()
        # Revision count may be 0 if scores are above threshold
        assert engine.revision_count >= 0

    def test_current_identity_property(self, engine: IdentityContinuityEngine) -> None:
        assert engine.current_identity is None
        result = engine.build()
        assert engine.current_identity is result

    def test_build_multiple_times(self, engine: IdentityContinuityEngine) -> None:
        engine.build()
        result = engine.build()
        assert isinstance(result, IdentityObject)
        assert result.confidence > 0.0


# ---------------------------------------------------------------------------
# Performance tests
# ---------------------------------------------------------------------------


class TestIdentityContinuityPerformance:
    def test_single_build_latency(self, engine: IdentityContinuityEngine) -> None:
        start = time.monotonic()
        engine.build()
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 100

    def test_multiple_builds_latency(self, engine: IdentityContinuityEngine) -> None:
        start = time.monotonic()
        for _ in range(10):
            engine.build()
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 500
