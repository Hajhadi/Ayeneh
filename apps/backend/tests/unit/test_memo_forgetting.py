"""Tests for MEM-08 Forgetting / Compression module."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ayeneh.memo.base import MemoryObject
from ayeneh.memo.forgetting.compression import (
    CompressionPlan,
    compress_conversation,
    compress_episode,
    compress_graph,
    compress_redundancy,
    compress_semantic,
    plan_compression,
)
from ayeneh.memo.forgetting.engine import (
    ForgettingEngine,
    analyse_importance,
    analyse_usage,
    classify_tier,
    compress_memory,
    detect_redundancy,
    generate_candidates,
    preserve_evidence,
)
from ayeneh.memo.forgetting.preservation import (
    PreservationRecord,
    create_preservation_record,
    must_preserve,
    validate_preservation,
)
from ayeneh.memo.forgetting.types import (
    AdaptiveForgettingTier,
    CompressionCandidate,
    CompressionObject,
    CompressionType,
    ForgettingResult,
    ResolutionLevel,
    RESOLUTION_ORDER,
    TIER_THRESHOLDS,
    UsageRecord,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_memory(
    identifier: str = 'mem_1',
    importance: float = 0.5,
    confidence: float = 0.7,
    evidence: tuple[str, ...] = ('ev1',),
    conversations: tuple[str, ...] = (),
    episodes: tuple[str, ...] = (),
    projects: tuple[str, ...] = (),
    lifecycle: str = 'validated_memory',
    age_hours: float = 1.0,
    memory_type: str = 'episodic',
) -> MemoryObject:
    return MemoryObject(
        identifier=identifier,
        memory_type=memory_type,
        creation_time=datetime.now(UTC) - timedelta(hours=age_hours + 1),
        last_updated=datetime.now(UTC) - timedelta(hours=age_hours),
        supporting_evidence=evidence,
        confidence=confidence,
        importance_score=importance,
        temporal_scope='short_term',
        associated_cognitive_objects=(),
        associated_episodes=episodes,
        associated_projects=projects,
        associated_conversations=conversations,
        lifecycle_status=lifecycle,
    )


# ---------------------------------------------------------------------------
# Usage analysis
# ---------------------------------------------------------------------------

class TestUsageAnalysis:
    def test_returns_usage_record(self) -> None:
        mem = _make_memory()
        record = analyse_usage(mem)
        assert isinstance(record, UsageRecord)
        assert record.memory_id == mem.identifier

    def test_frequency_score_in_range(self) -> None:
        mem = _make_memory()
        record = analyse_usage(mem)
        assert 0.0 <= record.access_frequency_score <= 1.0

    def test_recent_memory_higher_frequency(self) -> None:
        mem_recent = _make_memory(age_hours=1)
        mem_old = _make_memory(age_hours=200)
        r_recent = analyse_usage(mem_recent)
        r_old = analyse_usage(mem_old)
        assert r_recent.access_frequency_score > r_old.access_frequency_score

    def test_more_associations_higher_frequency(self) -> None:
        mem_sparse = _make_memory(conversations=(), episodes=())
        mem_rich = _make_memory(conversations=('c1', 'c2', 'c3'), episodes=('e1', 'e2'))
        r_sparse = analyse_usage(mem_sparse)
        r_rich = analyse_usage(mem_rich)
        assert r_rich.access_frequency_score >= r_sparse.access_frequency_score


# ---------------------------------------------------------------------------
# Tier classification
# ---------------------------------------------------------------------------

class TestTierClassification:
    def test_high_frequency_tier(self) -> None:
        assert classify_tier(0.9) == AdaptiveForgettingTier.FREQUENTLY_ACTIVE

    def test_mid_frequency_tier(self) -> None:
        assert classify_tier(0.6) == AdaptiveForgettingTier.OCCASIONALLY_ACTIVE

    def test_low_frequency_tier(self) -> None:
        assert classify_tier(0.3) == AdaptiveForgettingTier.DORMANT

    def test_very_low_frequency_tier(self) -> None:
        assert classify_tier(0.1) == AdaptiveForgettingTier.ARCHIVED

    def test_minimal_frequency_tier(self) -> None:
        assert classify_tier(0.01) == AdaptiveForgettingTier.HISTORICAL_ONLY

    def test_tier_thresholds_cover_full_range(self) -> None:
        for score_100 in range(101):
            tier = classify_tier(score_100 / 100.0)
            assert isinstance(tier, AdaptiveForgettingTier)


# ---------------------------------------------------------------------------
# Importance analysis
# ---------------------------------------------------------------------------

class TestImportanceAnalysis:
    def test_importance_in_range(self) -> None:
        mem = _make_memory(importance=0.5)
        score = analyse_importance(mem)
        assert 0.0 <= score <= 1.0

    def test_higher_base_importance_higher_score(self) -> None:
        mem_a = _make_memory(importance=0.2)
        mem_b = _make_memory(importance=0.9)
        assert analyse_importance(mem_b) > analyse_importance(mem_a)

    def test_core_lifecycle_bonus(self) -> None:
        mem_stable = _make_memory(importance=0.5, lifecycle='level_3_stable')
        mem_ephemeral = _make_memory(importance=0.5, lifecycle='level_0_ephemeral')
        assert analyse_importance(mem_stable) > analyse_importance(mem_ephemeral)


# ---------------------------------------------------------------------------
# Redundancy detection
# ---------------------------------------------------------------------------

class TestRedundancyDetection:
    def test_identical_evidence_detected(self) -> None:
        mem_a = _make_memory('a', evidence=('ev1', 'ev2'), memory_type='episodic')
        mem_b = _make_memory('b', evidence=('ev1', 'ev2'), memory_type='episodic')
        pairs = detect_redundancy([mem_a, mem_b], similarity_threshold=0.5)
        assert len(pairs) >= 1

    def test_different_evidence_not_detected(self) -> None:
        mem_a = _make_memory('a', evidence=('ev1',))
        mem_b = _make_memory('b', evidence=('ev2',))
        pairs = detect_redundancy([mem_a, mem_b], similarity_threshold=0.8)
        assert len(pairs) == 0

    def test_empty_list(self) -> None:
        assert detect_redundancy([]) == []


# ---------------------------------------------------------------------------
# Compression candidates
# ---------------------------------------------------------------------------

class TestCompressionCandidates:
    def test_dormant_low_importance_becomes_candidate(self) -> None:
        mem = _make_memory(importance=0.2, age_hours=500, confidence=0.5)
        usage = analyse_usage(mem)
        candidates = generate_candidates([mem], {mem.identifier: usage}, [])
        assert len(candidates) >= 1
        assert candidates[0].memory_id == mem.identifier

    def test_active_high_importance_not_candidate(self) -> None:
        mem = _make_memory(importance=0.9, age_hours=0.1, confidence=0.9, conversations=('c1', 'c2', 'c3'))
        usage = analyse_usage(mem)
        candidates = generate_candidates([mem], {mem.identifier: usage}, [])
        active_candidates = [c for c in candidates if c.compression_type != CompressionType.REDUNDANCY]
        assert len(active_candidates) == 0


# ---------------------------------------------------------------------------
# Evidence preservation
# ---------------------------------------------------------------------------

class TestEvidencePreservation:
    def test_preserve_evidence_returns_dict(self) -> None:
        mem = _make_memory()
        result = preserve_evidence(mem)
        assert isinstance(result, dict)
        assert result['memory_id'] == mem.identifier

    def test_preserve_evidence_has_key_fields(self) -> None:
        mem = _make_memory()
        result = preserve_evidence(mem)
        assert 'evidence_ids' in result
        assert 'confidence' in result
        assert 'importance' in result


# ---------------------------------------------------------------------------
# Memory compression
# ---------------------------------------------------------------------------

class TestMemoryCompression:
    def test_compression_object_created(self) -> None:
        mem = _make_memory()
        candidate = CompressionCandidate(
            memory_id=mem.identifier,
            compression_type=CompressionType.EPISODE,
            priority=0.8,
            rationale='test',
        )
        evidence = preserve_evidence(mem)
        result = compress_memory(mem, candidate, evidence)
        assert isinstance(result, CompressionObject)
        assert result.compression_strategy == CompressionType.EPISODE

    def test_information_reduced_in_range(self) -> None:
        mem = _make_memory()
        candidate = CompressionCandidate(
            memory_id=mem.identifier,
            compression_type=CompressionType.SEMANTIC,
            current_resolution=ResolutionLevel.RAW_CONVERSATION,
            target_resolution=ResolutionLevel.IDENTITY_LEVEL_UNDERSTANDING,
        )
        evidence = preserve_evidence(mem)
        result = compress_memory(mem, candidate, evidence)
        assert 0.0 <= result.information_reduced <= 1.0


# ---------------------------------------------------------------------------
# Forgetting engine
# ---------------------------------------------------------------------------

class TestForgettingEngine:
    def test_full_pipeline(self) -> None:
        memories = [_make_memory(f'mem_{i}', importance=i / 20.0, age_hours=i * 50) for i in range(10)]
        engine = ForgettingEngine()
        result = engine.run(memories)
        assert isinstance(result, ForgettingResult)
        assert result.memories_affected >= 0

    def test_empty_input(self) -> None:
        engine = ForgettingEngine()
        result = engine.run([])
        assert result.memories_affected == 0

    def test_result_recoverable(self) -> None:
        memories = [_make_memory(importance=0.1, age_hours=500)]
        engine = ForgettingEngine()
        result = engine.run(memories)
        assert result.recoverable is True


# ---------------------------------------------------------------------------
# Compression strategies
# ---------------------------------------------------------------------------

class TestCompressionStrategies:
    def test_redundancy_compression(self) -> None:
        mem_a = _make_memory('a', evidence=('ev1', 'ev2'))
        mem_b = _make_memory('b', evidence=('ev1', 'ev2'))
        plans = compress_redundancy([mem_a, mem_b])
        assert isinstance(plans, list)

    def test_conversation_compression(self) -> None:
        # compress_conversation checks temporal_scope == 'momentary' and memory_type == 'episodic'
        mem = MemoryObject(
            identifier='conv_mem',
            memory_type='episodic',
            creation_time=datetime.now(UTC),
            temporal_scope='momentary',
        )
        plans = compress_conversation([mem])
        assert len(plans) >= 1

    def test_episode_compression(self) -> None:
        # compress_episode checks age_days > 30, so age_hours must be > 720
        mem = _make_memory(memory_type='episodic', age_hours=800)
        plans = compress_episode([mem])
        assert len(plans) >= 1

    def test_semantic_compression(self) -> None:
        mem = _make_memory(memory_type='semantic_personal', importance=0.1)
        plans = compress_semantic([mem])
        assert len(plans) >= 1

    def test_plan_compression_all_strategies(self) -> None:
        mem = MemoryObject(
            identifier='plan_mem',
            memory_type='episodic',
            creation_time=datetime.now(UTC) - timedelta(hours=1000),
            last_updated=datetime.now(UTC) - timedelta(hours=1000),
            temporal_scope='momentary',
            importance_score=0.1,
            confidence=0.2,
        )
        plans = plan_compression([mem])
        assert isinstance(plans, list)


# ---------------------------------------------------------------------------
# Resolution levels
# ---------------------------------------------------------------------------

class TestResolutionLevels:
    def test_all_levels_present(self) -> None:
        assert len(RESOLUTION_ORDER) == 7

    def test_order_is_correct(self) -> None:
        assert RESOLUTION_ORDER[0] == ResolutionLevel.RAW_CONVERSATION
        assert RESOLUTION_ORDER[-1] == ResolutionLevel.IDENTITY_LEVEL_UNDERSTANDING


# ---------------------------------------------------------------------------
# Preservation
# ---------------------------------------------------------------------------

class TestPreservation:
    def test_must_preserve_core_memory(self) -> None:
        mem = _make_memory(lifecycle='longitudinal_memory')
        assert must_preserve(mem) is True

    def test_must_preserve_high_confidence_with_evidence(self) -> None:
        mem = _make_memory(confidence=0.9, evidence=('ev1',))
        assert must_preserve(mem) is True

    def test_must_preserve_high_importance(self) -> None:
        mem = _make_memory(importance=0.95)
        assert must_preserve(mem) is True

    def test_low_priority_not_preserved(self) -> None:
        mem = _make_memory(importance=0.2, confidence=0.3, evidence=(), lifecycle='validated_memory')
        assert must_preserve(mem) is False

    def test_create_preservation_record(self) -> None:
        mem = _make_memory()
        record = create_preservation_record(mem)
        assert isinstance(record, PreservationRecord)
        assert record.memory_id == mem.identifier

    def test_validate_preservation_passes(self) -> None:
        mem = _make_memory(evidence=('ev1', 'ev2'), confidence=0.8)
        record = create_preservation_record(mem)
        assert validate_preservation(mem, record) is True
