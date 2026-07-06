"""Unit tests for SELF-04 Self-Consistency types and engine."""

from __future__ import annotations

import pytest

from ayeneh.self_arch.self_consistency.types import (
    CONSISTENCY_LEVELS,
    CONSISTENCY_PHASES,
    CONFLICT_CATEGORIES,
    CONFIDENCE_DIMENSIONS,
    RESOLUTION_STRATEGIES,
    ConsistencyConfidence,
    ConsistencyIdentifier,
    ConsistencyObject,
    ConsistencyResult,
    ConflictDescriptor,
    CrossModuleRelationship,
    EvidenceItem,
    ExplainabilityMetadata,
    HealthIndicator,
    IntegrityCheck,
    ModuleConsistencyStatus,
    ResolutionAction,
)
from ayeneh.self_arch.self_consistency.engine import SelfConsistencyEngine


# ---------------------------------------------------------------------------
# Types tests
# ---------------------------------------------------------------------------


class TestConsistencyIdentifier:
    def test_default_creation(self) -> None:
        ident = ConsistencyIdentifier(id='c1')
        assert ident.id == 'c1'
        assert ident.version == 1

    def test_frozen(self) -> None:
        ident = ConsistencyIdentifier(id='c1')
        with pytest.raises(AttributeError):
            ident.id = 'c2'  # type: ignore[misc]


class TestModuleConsistencyStatus:
    def test_default_creation(self) -> None:
        status = ModuleConsistencyStatus(module_name='cog')
        assert status.module_name == 'cog'
        assert status.score == 0.0
        assert status.conflicts_detected == 0

    def test_custom_values(self) -> None:
        status = ModuleConsistencyStatus(
            module_name='inf',
            consistency_level='consistent',
            score=0.9,
            conflicts_detected=0,
        )
        assert status.score == 0.9


class TestConflictDescriptor:
    def test_default_creation(self) -> None:
        conflict = ConflictDescriptor(conflict_id='c1')
        assert conflict.conflict_id == 'c1'
        assert conflict.severity == 'medium'
        assert conflict.resolution_status == 'unresolved'

    def test_frozen(self) -> None:
        conflict = ConflictDescriptor(conflict_id='c1')
        with pytest.raises(AttributeError):
            conflict.severity = 'high'  # type: ignore[misc]


class TestCrossModuleRelationship:
    def test_default_creation(self) -> None:
        rel = CrossModuleRelationship(source_module='cog', target_module='inf')
        assert rel.source_module == 'cog'
        assert rel.target_module == 'inf'
        assert rel.consistency_score == 0.0


class TestConsistencyObject:
    def test_default_creation(self) -> None:
        obj = ConsistencyObject(consistency_id='c1')
        assert obj.consistency_id == 'c1'
        assert obj.resolution_status == 'unresolved'
        assert obj.confidence == 0.0

    def test_frozen(self) -> None:
        obj = ConsistencyObject(consistency_id='c1')
        with pytest.raises(AttributeError):
            obj.consistency_id = 'c2'  # type: ignore[misc]


class TestConsistencyResult:
    def test_default_creation(self) -> None:
        result = ConsistencyResult()
        assert result.consistency_id == ''
        assert result.confidence == 0.0
        assert result.duration_ms == 0.0
        assert len(result.errors) == 0

    def test_with_errors(self) -> None:
        result = ConsistencyResult(errors=('err1', 'err2'))
        assert len(result.errors) == 2


class TestHealthIndicator:
    def test_default_creation(self) -> None:
        indicator = HealthIndicator(indicator_name='module_health')
        assert indicator.indicator_name == 'module_health'
        assert indicator.is_healthy is True


class TestConstants:
    def test_consistency_levels(self) -> None:
        assert 'logical' in CONSISTENCY_LEVELS
        assert 'behavioral' in CONSISTENCY_LEVELS
        assert 'ethical' in CONSISTENCY_LEVELS
        assert len(CONSISTENCY_LEVELS) == 7

    def test_conflict_categories(self) -> None:
        assert 'logical_contradiction' in CONFLICT_CATEGORIES
        assert 'evidence_conflict' in CONFLICT_CATEGORIES
        assert len(CONFLICT_CATEGORIES) == 7

    def test_consistency_phases(self) -> None:
        assert 'architecture_state' in CONSISTENCY_PHASES
        assert 'architecture_health' in CONSISTENCY_PHASES
        assert len(CONSISTENCY_PHASES) == 8

    def test_resolution_strategies(self) -> None:
        assert 'automatic' in RESOLUTION_STRATEGIES
        assert 'escalation' in RESOLUTION_STRATEGIES

    def test_confidence_dimensions(self) -> None:
        assert 'evidence_strength' in CONFIDENCE_DIMENSIONS
        assert 'conflict_severity' in CONFIDENCE_DIMENSIONS


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestSelfConsistencyEngine:
    def setup_method(self) -> None:
        self.engine = SelfConsistencyEngine()

    def test_default_check(self) -> None:
        result = self.engine.check()
        assert result.consistency_id
        assert result.consistency_object is not None
        assert result.duration_ms >= 0

    def test_check_with_context(self) -> None:
        result = self.engine.check(
            context={'architecture_version': '2.0.0'},
            session_id='test-session',
        )
        assert result.consistency_id
        assert result.consistency_object.consistency_type in (
            'consistent', 'partially_consistent', 'inconsistent',
        )

    def test_check_detects_modules(self) -> None:
        result = self.engine.check()
        assert len(result.module_statuses) > 0
        module_names = [s.module_name for s in result.module_statuses]
        assert 'cog' in module_names
        assert 'inf' in module_names

    def test_check_analyzes_relationships(self) -> None:
        result = self.engine.check()
        assert len(result.relationships) > 0

    def test_check_generates_evidence(self) -> None:
        result = self.engine.check()
        assert len(result.evidence) > 0

    def test_check_computes_health_indicators(self) -> None:
        result = self.engine.check()
        assert len(result.health_indicators) > 0
        indicator_names = [h.indicator_name for h in result.health_indicators]
        assert 'module_health' in indicator_names

    def test_check_with_custom_modules(self) -> None:
        engine = SelfConsistencyEngine(modules=['cog', 'dec'])
        result = engine.check()
        module_names = [s.module_name for s in result.module_statuses]
        assert 'cog' in module_names
        assert 'dec' in module_names
        assert 'inf' not in module_names

    def test_check_with_low_scores(self) -> None:
        result = self.engine.check(
            context={'module_scores': {'cog': 0.3, 'inf': 0.2}},
        )
        assert len(result.conflicts) > 0

    def test_check_confidence_range(self) -> None:
        result = self.engine.check()
        assert 0.0 <= result.confidence <= 1.0

    def test_check_integrity_checks(self) -> None:
        result = self.engine.check()
        assert len(result.integrity_checks) > 0

    def test_check_result_is_frozen(self) -> None:
        result = self.engine.check()
        with pytest.raises(AttributeError):
            result.consistency_id = 'changed'  # type: ignore[misc]

    def test_check_explainability_metadata(self) -> None:
        result = self.engine.check()
        meta = result.consistency_object.explainability_metadata
        assert 'reasoning_chain' in meta
        assert len(meta['reasoning_chain']) > 0
