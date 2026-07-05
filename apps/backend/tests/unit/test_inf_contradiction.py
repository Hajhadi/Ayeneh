"""Comprehensive tests for INF-04 Contradiction Resolver."""

from __future__ import annotations

import pytest

from ayeneh.inf.contradiction.classification import ConflictClassifier
from ayeneh.inf.contradiction.engine import ContradictionResolver
from ayeneh.inf.contradiction.types import (
    CONTRADICTION_CATEGORIES,
    CONTRADICTION_SEVERITY_LEVELS,
    CONTRADICTION_STATUSES,
    RESOLUTION_STRATEGIES,
    ConflictClassification,
    ContradictionObject,
    ContradictionResult,
    EvidenceComparison,
    ResolutionPlan,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def resolver() -> ContradictionResolver:
    return ContradictionResolver()


@pytest.fixture
def classifier() -> ConflictClassifier:
    return ConflictClassifier()


class _FakeObj:
    def __init__(
        self,
        oid: str = '',
        itype: str = 'behavior',
        statement: str = '',
        confidence: float = 0.5,
        evidence: tuple[str, ...] = (),
        contradictions: tuple[str, ...] = (),
        status: str = '',
    ) -> None:
        self.inference_id = oid
        self.inference_type = itype
        self.statement = statement
        self.confidence = confidence
        self.supporting_evidence = evidence
        self.contradictions = contradictions
        self.current_status = status


# ---------------------------------------------------------------------------
# Types tests
# ---------------------------------------------------------------------------


class TestContradictionTypes:
    def test_categories_populated(self) -> None:
        assert len(CONTRADICTION_CATEGORIES) == 10
        assert 'belief' in CONTRADICTION_CATEGORIES
        assert 'meta_cognitive' in CONTRADICTION_CATEGORIES

    def test_strategies_populated(self) -> None:
        assert len(RESOLUTION_STRATEGIES) == 9
        assert 'evidence_accumulation' in RESOLUTION_STRATEGIES
        assert 'deferred_resolution' in RESOLUTION_STRATEGIES

    def test_severity_levels(self) -> None:
        assert CONTRADICTION_SEVERITY_LEVELS == [
            'negligible', 'minor', 'moderate', 'major', 'critical',
        ]

    def test_statuses(self) -> None:
        assert 'detected' in CONTRADICTION_STATUSES
        assert 'persistent' in CONTRADICTION_STATUSES

    def test_contradiction_object_frozen(self) -> None:
        obj = ContradictionObject(contradiction_id='c1')
        with pytest.raises(AttributeError):
            obj.contradiction_id = 'c2'  # type: ignore[misc]

    def test_contradiction_object_defaults(self) -> None:
        obj = ContradictionObject(contradiction_id='c1')
        assert obj.confidence == 0.0
        assert obj.severity == 0.0
        assert obj.current_status == 'detected'

    def test_contradiction_result_defaults(self) -> None:
        result = ContradictionResult()
        assert result.overall_consistency == 1.0
        assert len(result.contradictions) == 0

    def test_conflict_classification_defaults(self) -> None:
        cls = ConflictClassification()
        assert cls.category == 'belief'
        assert cls.scope == 'local'

    def test_evidence_comparison_defaults(self) -> None:
        comp = EvidenceComparison()
        assert comp.winner == ''

    def test_resolution_plan_defaults(self) -> None:
        plan = ResolutionPlan()
        assert plan.strategy == 'deferred_resolution'
        assert plan.safety_check == 'safe'


# ---------------------------------------------------------------------------
# Classifier tests
# ---------------------------------------------------------------------------


class TestConflictClassifier:
    def test_classify_returns_dict(self, classifier: ConflictClassifier) -> None:
        a = _FakeObj(oid='a', itype='belief', confidence=0.8)
        b = _FakeObj(oid='b', itype='belief', confidence=0.3)
        result = classifier.classify(a, b)
        assert 'classification' in result
        assert isinstance(result['classification'], ConflictClassification)

    def test_classify_category(self, classifier: ConflictClassifier) -> None:
        a = _FakeObj(oid='a', itype='identity', confidence=0.9)
        b = _FakeObj(oid='b', itype='identity', confidence=0.4)
        result = classifier.classify(a, b)
        assert result['category'] == 'identity'

    def test_classify_scope_global(self, classifier: ConflictClassifier) -> None:
        a = _FakeObj(oid='a', itype='identity', confidence=0.9)
        b = _FakeObj(oid='b', itype='identity', confidence=0.4)
        result = classifier.classify(a, b)
        assert result['scope'] == 'global'

    def test_classify_scope_local(self, classifier: ConflictClassifier) -> None:
        a = _FakeObj(oid='a', itype='behavior', confidence=0.9)
        b = _FakeObj(oid='b', itype='behavior', confidence=0.4)
        result = classifier.classify(a, b)
        assert result['scope'] == 'local'

    def test_identity_impact_high(self, classifier: ConflictClassifier) -> None:
        a = _FakeObj(oid='a', itype='identity', confidence=0.9)
        b = _FakeObj(oid='b', itype='identity', confidence=0.4)
        result = classifier.classify(a, b)
        assert result['identity_impact'] == 1.0

    def test_behavioral_impact_high(self, classifier: ConflictClassifier) -> None:
        a = _FakeObj(oid='a', itype='behavior', confidence=0.9)
        b = _FakeObj(oid='b', itype='behavior', confidence=0.4)
        result = classifier.classify(a, b)
        assert result['behavioral_impact'] == 1.0

    def test_severity_range(self, classifier: ConflictClassifier) -> None:
        a = _FakeObj(oid='a', itype='belief', confidence=1.0)
        b = _FakeObj(oid='b', itype='belief', confidence=0.0)
        result = classifier.classify(a, b)
        assert 0.0 <= result['severity'] <= 1.0


# ---------------------------------------------------------------------------
# Resolver engine tests
# ---------------------------------------------------------------------------


class TestContradictionResolver:
    def test_process_returns_result(self, resolver: ContradictionResolver) -> None:
        result = resolver.process([])
        assert isinstance(result, ContradictionResult)

    def test_process_empty_input(self, resolver: ContradictionResolver) -> None:
        result = resolver.process([])
        assert result.overall_consistency == 1.0
        assert len(result.contradictions) == 0

    def test_process_single_object(self, resolver: ContradictionResolver) -> None:
        obj = _FakeObj(oid='a', itype='belief', confidence=0.7)
        result = resolver.process([obj])
        assert isinstance(result, ContradictionResult)
        assert len(result.contradictions) == 0

    def test_detects_same_type_different_statement(self, resolver: ContradictionResolver) -> None:
        a = _FakeObj(oid='a', itype='belief', statement='X is true', confidence=0.8)
        b = _FakeObj(oid='b', itype='belief', statement='X is false', confidence=0.6)
        result = resolver.process([a, b])
        assert len(result.contradictions) >= 1

    def test_no_contradiction_different_types(self, resolver: ContradictionResolver) -> None:
        a = _FakeObj(oid='a', itype='belief', statement='X', confidence=0.8)
        b = _FakeObj(oid='b', itype='goal', statement='Y', confidence=0.6)
        result = resolver.process([a, b])
        assert len(result.contradictions) == 0

    def test_consistency_score(self, resolver: ContradictionResolver) -> None:
        a = _FakeObj(oid='a', itype='behavior', statement='X', confidence=0.8)
        b = _FakeObj(oid='b', itype='behavior', statement='X', confidence=0.8)
        result = resolver.process([a, b])
        assert result.overall_consistency == 1.0

    def test_classifications_populated(self, resolver: ContradictionResolver) -> None:
        a = _FakeObj(oid='a', itype='belief', statement='X is true', confidence=0.8)
        b = _FakeObj(oid='b', itype='belief', statement='X is false', confidence=0.6)
        result = resolver.process([a, b])
        assert len(result.classifications) == len(result.contradictions)

    def test_evidence_comparisons_populated(self, resolver: ContradictionResolver) -> None:
        a = _FakeObj(oid='a', itype='belief', statement='X', confidence=0.8)
        b = _FakeObj(oid='b', itype='belief', statement='Y', confidence=0.6)
        result = resolver.process([a, b])
        assert len(result.evidence_comparisons) == len(result.contradictions)

    def test_resolution_plans_populated(self, resolver: ContradictionResolver) -> None:
        a = _FakeObj(oid='a', itype='belief', statement='X', confidence=0.8)
        b = _FakeObj(oid='b', itype='belief', statement='Y', confidence=0.6)
        result = resolver.process([a, b])
        assert len(result.resolution_plans) == len(result.contradictions)

    def test_process_with_context(self, resolver: ContradictionResolver) -> None:
        result = resolver.process([], {'session_id': 's1'})
        assert isinstance(result, ContradictionResult)
        assert result.processing_metadata.get('session_id') == 's1'

    def test_detects_explicit_contradiction_ref(self, resolver: ContradictionResolver) -> None:
        a = _FakeObj(oid='a', itype='belief', contradictions=('b',))
        b = _FakeObj(oid='b', itype='belief')
        result = resolver.process([a, b])
        assert len(result.contradictions) >= 1

    def test_resolved_vs_persistent_ids(self, resolver: ContradictionResolver) -> None:
        a = _FakeObj(oid='a', itype='belief', statement='X', confidence=0.8)
        b = _FakeObj(oid='b', itype='belief', statement='Y', confidence=0.6)
        result = resolver.process([a, b])
        all_ids = set(result.resolved_ids) | set(result.persistent_ids)
        assert all_ids == {c.contradiction_id for c in result.contradictions}

    def test_identity_category_selects_strategy(self, resolver: ContradictionResolver) -> None:
        a = _FakeObj(oid='a', itype='identity', statement='I am A', confidence=0.9)
        b = _FakeObj(oid='b', itype='identity', statement='I am B', confidence=0.5)
        result = resolver.process([a, b])
        assert len(result.resolution_plans) == 1
        assert result.resolution_plans[0].strategy == 'identity_restructuring'

    def test_none_objects_filtered(self, resolver: ContradictionResolver) -> None:
        result = resolver.process([None, None])
        assert isinstance(result, ContradictionResult)
        assert len(result.contradictions) == 0
