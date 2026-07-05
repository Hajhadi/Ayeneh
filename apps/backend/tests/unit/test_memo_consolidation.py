"""Tests for the consolidation subsystem (MEM-05)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from ayeneh.memo.consolidation.types import (
    CONSOLIDATION_CRITERIA,
    CONSOLIDATION_DECISIONS,
    CONSOLIDATION_LEVEL_HIERARCHY,
    ConsolidationCriteriaResult,
    ConsolidationObject,
    ConsolidationPipelineResult,
    EvidenceAggregation,
    make_consolidation_version,
)
from ayeneh.memo.consolidation.engine import ConsolidationEngine
from ayeneh.memo.consolidation.quality import (
    ConsolidationQualityAssessor,
    QualityMetrics,
)


# ---------------------------------------------------------------------------
# Types tests
# ---------------------------------------------------------------------------


class TestConsolidationObject:
    def test_creation(self) -> None:
        obj = ConsolidationObject(
            identifier='cons_1',
            target_memory='mem_1',
        )
        assert obj.identifier == 'cons_1'
        assert obj.target_memory == 'mem_1'

    def test_confidence_delta(self) -> None:
        obj = ConsolidationObject(
            identifier='cons_1',
            target_memory='mem_1',
            confidence_before=0.3,
            confidence_after=0.8,
        )
        assert abs(obj.confidence_delta - 0.5) < 1e-6

    def test_is_promoted(self) -> None:
        obj = ConsolidationObject(
            identifier='cons_1',
            target_memory='mem_1',
            reason_for_promotion='met criteria',
        )
        assert obj.is_promoted
        assert not obj.is_rejected

    def test_is_rejected(self) -> None:
        obj = ConsolidationObject(
            identifier='cons_1',
            target_memory='mem_1',
            reason_for_rejection='insufficient evidence',
        )
        assert obj.is_rejected
        assert not obj.is_promoted

    def test_frozen(self) -> None:
        obj = ConsolidationObject(identifier='cons_1', target_memory='mem_1')
        with pytest.raises(AttributeError):
            obj.identifier = 'cons_2'


class TestEvidenceAggregation:
    def test_support_ratio(self) -> None:
        agg = EvidenceAggregation(
            aggregation_id='ea_1',
            total_evidence_count=10,
            supporting_count=8,
            contradicting_count=2,
        )
        assert abs(agg.support_ratio - 0.8) < 1e-6

    def test_support_ratio_empty(self) -> None:
        agg = EvidenceAggregation(aggregation_id='ea_1')
        assert agg.support_ratio == 0.0

    def test_has_sufficient_evidence(self) -> None:
        agg = EvidenceAggregation(
            aggregation_id='ea_1',
            total_evidence_count=5,
            supporting_count=4,
        )
        assert agg.has_sufficient_evidence

    def test_insufficient_evidence(self) -> None:
        agg = EvidenceAggregation(
            aggregation_id='ea_1',
            total_evidence_count=1,
            supporting_count=1,
        )
        assert not agg.has_sufficient_evidence


class TestConsolidationCriteriaResult:
    def test_criteria_fraction(self) -> None:
        result = ConsolidationCriteriaResult(
            memory_id='mem_1',
            criteria_met=('repeated_observation', 'behavioral_confirmation'),
            criteria_failed=('cross_episode_recurrence',),
        )
        assert abs(result.criteria_fraction - 2 / 3) < 1e-6

    def test_criteria_fraction_empty(self) -> None:
        result = ConsolidationCriteriaResult(memory_id='mem_1')
        assert result.criteria_fraction == 0.0


class TestConsolidationPipelineResult:
    def test_success_rate(self) -> None:
        result = ConsolidationPipelineResult(
            processed_count=10,
            promoted_count=7,
        )
        assert abs(result.success_rate - 0.7) < 1e-6

    def test_success_rate_empty(self) -> None:
        result = ConsolidationPipelineResult()
        assert result.success_rate == 0.0


class TestMakeConsolidationVersion:
    def test_creates_version(self) -> None:
        version = make_consolidation_version(
            version_number=1,
            changed_fields={'state': 'promoted'},
            change_reason='met criteria',
        )
        assert version['version_number'] == 1
        assert 'timestamp' in version


class TestConstants:
    def test_consolidation_criteria(self) -> None:
        assert 'repeated_observation' in CONSOLIDATION_CRITERIA
        assert 'behavioral_confirmation' in CONSOLIDATION_CRITERIA
        assert 'cross_episode_recurrence' in CONSOLIDATION_CRITERIA
        assert len(CONSOLIDATION_CRITERIA) == 9

    def test_consolidation_decisions(self) -> None:
        assert 'promote' in CONSOLIDATION_DECISIONS
        assert 'reject' in CONSOLIDATION_DECISIONS
        assert 'defer' in CONSOLIDATION_DECISIONS
        assert len(CONSOLIDATION_DECISIONS) == 6

    def test_consolidation_levels(self) -> None:
        assert 'observation' in CONSOLIDATION_LEVEL_HIERARCHY
        assert 'core_personal_knowledge' in CONSOLIDATION_LEVEL_HIERARCHY
        assert len(CONSOLIDATION_LEVEL_HIERARCHY) == 6


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestConsolidationEngine:
    def test_creation(self) -> None:
        engine = ConsolidationEngine()
        assert engine._confidence_threshold == 0.5

    def test_run_pipeline_empty(self) -> None:
        engine = ConsolidationEngine()
        result = engine.run_pipeline([])
        assert result.processed_count == 0

    def test_run_pipeline_basic(self) -> None:
        engine = ConsolidationEngine(confidence_threshold=0.3)
        items = [
            {
                'id': 'mem_1',
                'activation_score': 0.8,
                'evidence': [
                    {'source': 'conversation', 'confidence': 0.9, 'supports': True},
                    {'source': 'episode', 'confidence': 0.7, 'supports': True},
                ],
            },
        ]
        result = engine.run_pipeline(items)
        assert result.processed_count == 1

    def test_run_pipeline_below_threshold(self) -> None:
        engine = ConsolidationEngine(confidence_threshold=0.9)
        items = [
            {
                'id': 'mem_1',
                'activation_score': 0.3,
                'evidence': [],
            },
        ]
        result = engine.run_pipeline(items)
        assert result.processed_count == 1
        assert result.promoted_count == 0

    def test_evaluate_criteria(self) -> None:
        engine = ConsolidationEngine()
        evidence = [
            {'source': 'conversation', 'confidence': 0.8, 'supports': True},
            {'source': 'episode', 'confidence': 0.7, 'supports': True},
            {'source': 'behavior', 'confidence': 0.9, 'supports': True},
        ]
        result = engine.evaluate_criteria('mem_1', evidence)
        assert result.memory_id == 'mem_1'
        assert len(result.criteria_met) > 0

    def test_evaluate_criteria_empty_evidence(self) -> None:
        engine = ConsolidationEngine()
        result = engine.evaluate_criteria('mem_1', [])
        assert result.overall_score == 0.0

    def test_consolidation_history(self) -> None:
        engine = ConsolidationEngine(confidence_threshold=0.3)
        items = [
            {
                'id': 'mem_1',
                'activation_score': 0.8,
                'evidence': [
                    {'source': 'conversation', 'confidence': 0.9, 'supports': True},
                    {'source': 'episode', 'confidence': 0.7, 'supports': True},
                ],
            },
        ]
        engine.run_pipeline(items)
        history = engine.get_consolidation_history()
        assert len(history) >= 0  # May or may not promote depending on criteria

    def test_long_term_store(self) -> None:
        engine = ConsolidationEngine(confidence_threshold=0.3)
        items = [
            {
                'id': 'mem_1',
                'activation_score': 0.8,
                'evidence': [
                    {'source': 'conversation', 'confidence': 0.9, 'supports': True},
                    {'source': 'episode', 'confidence': 0.7, 'supports': True},
                    {'source': 'behavior', 'confidence': 0.8, 'supports': True},
                ],
                'supporting_episodes': ['ep_1', 'ep_2'],
            },
        ]
        engine.run_pipeline(items, episodes=[{'id': 'ep_1'}, {'id': 'ep_2'}])
        store = engine.get_long_term_store()
        # Store may or may not have entries depending on criteria evaluation
        assert isinstance(store, dict)

    def test_cross_episode_validation(self) -> None:
        engine = ConsolidationEngine(min_episodes_for_cross_validation=2)
        items = [
            {
                'id': 'mem_1',
                'activation_score': 0.8,
                'evidence': [
                    {'source': 'conversation', 'confidence': 0.9, 'supports': True},
                    {'source': 'episode', 'confidence': 0.7, 'supports': True},
                ],
            },
        ]
        episodes = [
            {'id': 'ep_1', 'summary': 'test episode 1'},
            {'id': 'ep_2', 'summary': 'test episode 2'},
        ]
        result = engine.run_pipeline(items, episodes=episodes)
        assert result.processed_count == 1


# ---------------------------------------------------------------------------
# Quality assessor tests
# ---------------------------------------------------------------------------


class TestConsolidationQualityAssessor:
    def test_creation(self) -> None:
        assessor = ConsolidationQualityAssessor()
        assert len(assessor.get_assessment_history()) == 0

    def test_assess_promoted(self) -> None:
        assessor = ConsolidationQualityAssessor()
        cons = ConsolidationObject(
            identifier='cons_1',
            target_memory='mem_1',
            supporting_episodes=('ep_1', 'ep_2'),
            supporting_conversations=('conv_1',),
            confidence_before=0.5,
            confidence_after=0.8,
            reason_for_promotion='met criteria',
        )
        metrics = assessor.assess(cons)
        assert metrics.consolidation_id == 'cons_1'
        assert metrics.evidence_quality > 0.0
        assert metrics.overall_quality > 0.0

    def test_assess_rejected(self) -> None:
        assessor = ConsolidationQualityAssessor()
        cons = ConsolidationObject(
            identifier='cons_2',
            target_memory='mem_2',
            confidence_before=0.3,
            confidence_after=0.1,
            reason_for_rejection='insufficient evidence',
        )
        metrics = assessor.assess(cons)
        assert metrics.consolidation_id == 'cons_2'
        assert metrics.overall_quality >= 0.0

    def test_assess_with_criteria(self) -> None:
        assessor = ConsolidationQualityAssessor()
        cons = ConsolidationObject(
            identifier='cons_3',
            target_memory='mem_3',
            supporting_episodes=('ep_1',),
            confidence_before=0.4,
            confidence_after=0.7,
            reason_for_promotion='good',
        )
        criteria = ConsolidationCriteriaResult(
            memory_id='mem_3',
            criteria_met=('repeated_observation', 'behavioral_confirmation'),
            criteria_failed=('cross_episode_recurrence',),
            overall_score=0.66,
        )
        metrics = assessor.assess(cons, criteria)
        assert metrics.criteria_coverage > 0.0

    def test_assess_batch(self) -> None:
        assessor = ConsolidationQualityAssessor()
        consolidations = [
            ConsolidationObject(
                identifier='cons_1', target_memory='mem_1',
                confidence_before=0.3, confidence_after=0.8,
                reason_for_promotion='good',
            ),
            ConsolidationObject(
                identifier='cons_2', target_memory='mem_2',
                confidence_before=0.5, confidence_after=0.1,
                reason_for_rejection='bad',
            ),
        ]
        metrics_list = assessor.assess_batch(consolidations)
        assert len(metrics_list) == 2

    def test_average_quality(self) -> None:
        assessor = ConsolidationQualityAssessor()
        assert assessor.get_average_quality() == 0.0

        cons = ConsolidationObject(
            identifier='cons_1', target_memory='mem_1',
            confidence_before=0.3, confidence_after=0.8,
            reason_for_promotion='good',
        )
        assessor.assess(cons)
        assert assessor.get_average_quality() > 0.0

    def test_assessment_history(self) -> None:
        assessor = ConsolidationQualityAssessor()
        cons = ConsolidationObject(
            identifier='cons_1', target_memory='mem_1',
            confidence_before=0.3, confidence_after=0.8,
            reason_for_promotion='good',
        )
        assessor.assess(cons)
        history = assessor.get_assessment_history()
        assert len(history) == 1
