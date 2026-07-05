"""Tests for MEM-07 Ranking module."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ayeneh.memo.base import MemoryObject
from ayeneh.memo.ranking.diversity import (
    DiversityConfig,
    _cluster_key,
    diversify_selection,
)
from ayeneh.memo.ranking.engine import (
    RankingEngine,
    composite_rank,
    detect_conflicts,
    estimate_importance,
    estimate_relevance,
    extract_features,
    match_context,
    select_working_memory,
    weight_evidence,
)
from ayeneh.memo.ranking.types import (
    ConflictRecord,
    DimensionScores,
    RankingContext,
    RankingDimension,
    RankingObject,
    TaskProfile,
    TASK_PROFILE_WEIGHTS,
    WorkingMemorySelection,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_memory(
    identifier: str = 'mem_1',
    importance: float = 0.5,
    confidence: float = 0.7,
    evidence: tuple[str, ...] = ('ev1',),
    episodes: tuple[str, ...] = (),
    projects: tuple[str, ...] = (),
    cognitive_objects: tuple[str, ...] = (),
    lifecycle: str = 'validated_memory',
    age_hours: float = 1.0,
) -> MemoryObject:
    return MemoryObject(
        identifier=identifier,
        memory_type='episodic',
        creation_time=datetime.now(UTC) - timedelta(hours=age_hours + 1),
        last_updated=datetime.now(UTC) - timedelta(hours=age_hours),
        supporting_evidence=evidence,
        confidence=confidence,
        importance_score=importance,
        temporal_scope='short_term',
        associated_cognitive_objects=cognitive_objects,
        associated_episodes=episodes,
        associated_projects=projects,
        lifecycle_status=lifecycle,
    )


def _context(**kwargs) -> RankingContext:
    defaults = {
        'task_profile': TaskProfile.DEBUGGING,
        'current_goals': ('goal_a',),
        'active_projects': ('proj_a',),
    }
    defaults.update(kwargs)
    return RankingContext(**defaults)


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

class TestFeatureExtraction:
    def test_returns_all_dimensions(self) -> None:
        mem = _make_memory()
        dims = extract_features(mem, _context())
        for dim in RankingDimension:
            assert dim.value in dims.scores

    def test_scores_in_range(self) -> None:
        mem = _make_memory()
        dims = extract_features(mem, _context())
        for score in dims.scores.values():
            assert 0.0 <= score <= 1.0

    def test_recent_memory_high_relevance(self) -> None:
        mem = _make_memory(age_hours=0.1)
        dims = extract_features(mem, _context())
        assert dims.score(RankingDimension.CURRENT_RELEVANCE) > 0.9

    def test_old_memory_low_relevance(self) -> None:
        mem = _make_memory(age_hours=200)
        dims = extract_features(mem, _context())
        assert dims.score(RankingDimension.CURRENT_RELEVANCE) < 0.5

    def test_high_evidence_gives_evidence_quality(self) -> None:
        mem = _make_memory(evidence=('ev1', 'ev2', 'ev3'))
        dims = extract_features(mem, _context())
        assert dims.score(RankingDimension.EVIDENCE_QUALITY) == 1.0

    def test_raw_features_populated(self) -> None:
        mem = _make_memory()
        dims = extract_features(mem, _context())
        assert 'age_hours' in dims.raw_features
        assert 'confidence' in dims.raw_features


# ---------------------------------------------------------------------------
# Relevance estimation
# ---------------------------------------------------------------------------

class TestRelevanceEstimation:
    def test_relevance_in_range(self) -> None:
        mem = _make_memory()
        dims = extract_features(mem, _context())
        rel = estimate_relevance(dims, _context())
        assert 0.0 <= rel <= 1.0

    def test_recent_memory_high_relevance(self) -> None:
        mem = _make_memory(age_hours=0.1)
        dims = extract_features(mem, _context())
        rel = estimate_relevance(dims, _context())
        assert rel > 0.3


# ---------------------------------------------------------------------------
# Importance estimation
# ---------------------------------------------------------------------------

class TestImportanceEstimation:
    def test_importance_in_range(self) -> None:
        mem = _make_memory(importance=0.8)
        dims = extract_features(mem, _context())
        imp = estimate_importance(dims, mem)
        assert 0.0 <= imp <= 1.0

    def test_consolidated_memory_higher_importance(self) -> None:
        mem_a = _make_memory(importance=0.5, lifecycle='validated_memory')
        mem_b = _make_memory(importance=0.5, lifecycle='consolidated_memory')
        dims_a = extract_features(mem_a, _context())
        dims_b = extract_features(mem_b, _context())
        imp_a = estimate_importance(dims_a, mem_a)
        imp_b = estimate_importance(dims_b, mem_b)
        assert imp_b >= imp_a


# ---------------------------------------------------------------------------
# Context matching
# ---------------------------------------------------------------------------

class TestContextMatching:
    def test_match_context_in_range(self) -> None:
        mem = _make_memory()
        dims = extract_features(mem, _context())
        score = match_context(dims, _context())
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# Evidence weighting
# ---------------------------------------------------------------------------

class TestEvidenceWeighting:
    def test_weight_evidence_in_range(self) -> None:
        mem = _make_memory(confidence=0.9)
        dims = extract_features(mem, _context())
        score = weight_evidence(dims, mem)
        assert 0.0 <= score <= 1.0

    def test_high_confidence_higher_weight(self) -> None:
        mem_hi = _make_memory(confidence=0.95)
        mem_lo = _make_memory(confidence=0.2)
        dims_hi = extract_features(mem_hi, _context())
        dims_lo = extract_features(mem_lo, _context())
        assert weight_evidence(dims_hi, mem_hi) >= weight_evidence(dims_lo, mem_lo)


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

class TestConflictDetection:
    def test_no_conflicts_for_identical_types(self) -> None:
        mem_a = _make_memory('mem_a')
        mem_b = _make_memory('mem_b')
        conflicts = detect_conflicts([(mem_a, 0.8), (mem_b, 0.7)])
        assert len(conflicts) == 0

    def test_conflicts_with_shared_evidence(self) -> None:
        mem_a = MemoryObject(
            identifier='mem_a',
            memory_type='episodic',
            creation_time=datetime.now(UTC),
            supporting_evidence=('ev1', 'ev2'),
        )
        # Manually create different types
        mem_b = MemoryObject(
            identifier='mem_b',
            memory_type='semantic_personal',
            creation_time=datetime.now(UTC),
            supporting_evidence=('ev1', 'ev2'),
        )
        conflicts = detect_conflicts([(mem_a, 0.8), (mem_b, 0.7)])
        assert len(conflicts) > 0
        assert conflicts[0].conflict_type == 'evidence_overlap'


# ---------------------------------------------------------------------------
# Composite ranking
# ---------------------------------------------------------------------------

class TestCompositeRanking:
    def test_composite_rank_returns_ranking_object(self) -> None:
        mem = _make_memory()
        dims = extract_features(mem, _context())
        rank = composite_rank(
            mem, dims,
            relevance=0.8,
            importance=0.6,
            context_match=0.5,
            evidence_weight=0.7,
            task_profile=TaskProfile.DEBUGGING,
        )
        assert isinstance(rank, RankingObject)
        assert rank.target_memory == mem.identifier
        assert 0.0 <= rank.overall_score <= 1.0

    def test_higher_scores_yield_higher_overall(self) -> None:
        mem = _make_memory()
        dims = extract_features(mem, _context())
        rank_high = composite_rank(mem, dims, 0.9, 0.9, 0.9, 0.9, TaskProfile.DEBUGGING)
        rank_low = composite_rank(mem, dims, 0.1, 0.1, 0.1, 0.1, TaskProfile.DEBUGGING)
        assert rank_high.overall_score > rank_low.overall_score


# ---------------------------------------------------------------------------
# Working memory selection
# ---------------------------------------------------------------------------

class TestWorkingMemorySelection:
    def test_selects_top_n(self) -> None:
        rankings = []
        for i in range(30):
            rankings.append(
                RankingObject(
                    ranking_identifier=f'r{i}',
                    target_memory=f'mem_{i}',
                    overall_score=i / 30.0,
                )
            )
        selection = select_working_memory(rankings, capacity=10)
        assert len(selection.selected_memories) == 10
        assert selection.capacity_used == 10

    def test_all_selected_if_fewer_than_capacity(self) -> None:
        rankings = [
            RankingObject(ranking_identifier='r1', target_memory='m1', overall_score=0.9),
        ]
        selection = select_working_memory(rankings, capacity=20)
        assert len(selection.selected_memories) == 1

    def test_empty_input(self) -> None:
        selection = select_working_memory([], capacity=10)
        assert len(selection.selected_memories) == 0


# ---------------------------------------------------------------------------
# Ranking engine
# ---------------------------------------------------------------------------

class TestRankingEngine:
    def test_full_pipeline(self) -> None:
        memories = [_make_memory(f'mem_{i}', importance=i / 10.0) for i in range(5)]
        engine = RankingEngine(default_capacity=3)
        result = engine.rank(memories, _context())
        assert isinstance(result, WorkingMemorySelection)
        assert len(result.selected_memories) <= 3

    def test_empty_memories(self) -> None:
        engine = RankingEngine()
        result = engine.rank([], _context())
        assert len(result.selected_memories) == 0

    def test_with_conflicts(self) -> None:
        mem_a = MemoryObject(
            identifier='a', memory_type='episodic',
            creation_time=datetime.now(UTC),
            supporting_evidence=('ev1',),
        )
        mem_b = MemoryObject(
            identifier='b', memory_type='semantic_personal',
            creation_time=datetime.now(UTC),
            supporting_evidence=('ev1',),
        )
        engine = RankingEngine()
        result = engine.rank([mem_a, mem_b], _context())
        assert len(result.rankings) == 2


# ---------------------------------------------------------------------------
# Task profile weights
# ---------------------------------------------------------------------------

class TestTaskProfiles:
    def test_all_profiles_have_all_dimensions(self) -> None:
        for profile, weights in TASK_PROFILE_WEIGHTS.items():
            for dim in RankingDimension:
                assert dim.value in weights, f'{profile} missing {dim}'

    def test_weights_sum_to_one(self) -> None:
        for profile, weights in TASK_PROFILE_WEIGHTS.items():
            total = sum(weights.values())
            assert abs(total - 1.0) < 0.01, f'{profile} weights sum to {total}'


# ---------------------------------------------------------------------------
# Diversity
# ---------------------------------------------------------------------------

class TestDiversity:
    def test_cluster_key(self) -> None:
        r = RankingObject(
            ranking_identifier='r1', target_memory='m1',
            identity_impact_score=0.8,
        )
        assert _cluster_key(r) == 'identity'

    def test_diversify_reduces_size(self) -> None:
        rankings = [
            RankingObject(
                ranking_identifier=f'r{i}',
                target_memory=f'm{i}',
                overall_score=0.9 - i * 0.01,
                behavioral_impact_score=0.9 if i < 10 else 0.1,
            )
            for i in range(30)
        ]
        result = diversify_selection(rankings, target_size=10)
        assert len(result) == 10

    def test_diversify_preserves_high_relevance(self) -> None:
        rankings = [
            RankingObject(
                ranking_identifier='r0',
                target_memory='m0',
                overall_score=1.0,
            )
        ]
        result = diversify_selection(rankings, target_size=5)
        assert result[0].target_memory == 'm0'
