"""Integration tests for Memory Evolution — Phase 2: algorithms.

Covers: semantic merge, contradiction detection, strengthening, weakening,
confidence evolution, importance evolution, lineage preservation,
idempotency, concurrent evolution, consolidation pipeline.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ayeneh.application.services.memory_evolution import (
    EvolutionConfig,
    EvolutionReason,
    EvolutionType,
    MemoryEvolutionService,
)
from ayeneh.infrastructure.persistence.base import Base
from ayeneh.infrastructure.persistence.models.memory import MemoryModel
from ayeneh.infrastructure.persistence.models.user import UserModel
from ayeneh.infrastructure.persistence.unit_of_work import UnitOfWork


def _utcnow() -> datetime:
    return datetime.now(UTC)


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
def uow_factory(session_factory):
    def factory():
        return UnitOfWork(session_factory)
    return factory


@pytest_asyncio.fixture
async def user_id(session_factory) -> str:
    uid = uuid.uuid4()
    async with session_factory() as session:
        session.add(UserModel(
            id=uid, email=f"{uid}@test.com", status="active",
            preferences={}, created_at=_utcnow(), updated_at=_utcnow(),
        ))
        await session.commit()
    return str(uid)


@pytest_asyncio.fixture
def evo_service(uow_factory):
    return MemoryEvolutionService(
        uow_factory=uow_factory,
        config=EvolutionConfig(
            merge_similarity_threshold=0.92,
            contradiction_similarity_threshold=0.50,
            strengthen_boost=0.10,
            weaken_factor=0.05,
            weaken_min_confidence=0.05,
            stale_days_threshold=60,
            importance_boost=0.08,
            importance_decay_factor=0.90,
        ),
    )


async def _create_mem(session_factory, user_id: str, content: str,
                      memory_type: str = "semantic", confidence: float = 0.5,
                      created_days_ago: int = 0, updated_days_ago: int | None = None) -> str:
    mid = uuid.uuid4()
    now = datetime.now(UTC)
    created = now - timedelta(days=created_days_ago)
    updated = now - timedelta(days=updated_days_ago if updated_days_ago is not None else created_days_ago)
    async with session_factory() as session:
        session.add(MemoryModel(
            id=mid, user_id=uuid.UUID(user_id), type=memory_type,
            content=content, confidence=confidence, source_message_ids=[],
            status="active", created_at=created, updated_at=updated,
            importance_history={"initial": 0.5},
            confidence_history={"initial": confidence},
        ))
        await session.commit()
    return str(mid)


# ════════════════════════════════════════════════════════════════════════
# Semantic merge tests
# ════════════════════════════════════════════════════════════════════════

class TestSemanticMerge:
    @pytest.mark.asyncio
    async def test_merge_combines_content(self, evo_service, user_id, session_factory):
        m1 = await _create_mem(session_factory, user_id, "I value honesty in all things")
        m2 = await _create_mem(session_factory, user_id, "I value honesty in relationships")
        merged_id = await evo_service.merge_memories([m1, m2], user_id)
        merged = await evo_service._get_snapshot(merged_id)
        assert merged is not None
        assert "honesty" in merged.content
        assert merged.confidence >= 0.5

    @pytest.mark.asyncio
    async def test_merge_records_lineage(self, evo_service, user_id, session_factory):
        m1 = await _create_mem(session_factory, user_id, "Fact A about learning")
        m2 = await _create_mem(session_factory, user_id, "Fact A about growth")
        merged_id = await evo_service.merge_memories([m1, m2], user_id)
        descendants = await evo_service.get_descendants(m1)
        assert len(descendants) == 1
        assert str(descendants[0].descendant_id) == merged_id
        assert descendants[0].relation == "merged_into"

    @pytest.mark.asyncio
    async def test_merge_creates_evolution_records(self, evo_service, user_id, session_factory):
        m1 = await _create_mem(session_factory, user_id, "Alpha learning")
        m2 = await _create_mem(session_factory, user_id, "Alpha growing")
        await evo_service.merge_memories([m1, m2], user_id)
        h1 = await evo_service.get_evolution_history(m1)
        assert any(r.evolution_type == EvolutionType.MERGED for r in h1)

    @pytest.mark.asyncio
    async def test_merge_supersedes_originals(self, evo_service, user_id, session_factory):
        m1 = await _create_mem(session_factory, user_id, "Original fact one")
        m2 = await _create_mem(session_factory, user_id, "Original fact two")
        await evo_service.merge_memories([m1, m2], user_id)
        snap1 = await evo_service._get_snapshot(m1)
        assert snap1 is not None and snap1.status == "superseded"

    @pytest.mark.asyncio
    async def test_detect_and_merge_similar(self, evo_service, user_id, session_factory):
        await _create_mem(session_factory, user_id, "I value honesty and transparency in all my relationships", confidence=0.6)
        await _create_mem(session_factory, user_id, "I value honesty and transparency in all my relationships", confidence=0.7)
        count = await evo_service.detect_and_merge_similar(user_id)
        assert count == 1

    @pytest.mark.asyncio
    async def test_merge_preserves_highest_confidence(self, evo_service, user_id, session_factory):
        m1 = await _create_mem(session_factory, user_id, "Important fact about work", confidence=0.4)
        m2 = await _create_mem(session_factory, user_id, "Important fact about my work", confidence=0.9)
        merged_id = await evo_service.merge_memories([m1, m2], user_id)
        merged = await evo_service._get_snapshot(merged_id)
        assert merged is not None and merged.confidence == 0.9


# ════════════════════════════════════════════════════════════════════════
# Contradiction detection tests
# ════════════════════════════════════════════════════════════════════════

class TestContradictionDetection:
    @pytest.mark.asyncio
    async def test_detects_contradiction(self, evo_service, user_id, session_factory):
        await _create_mem(session_factory, user_id, "I do not enjoy meetings at work", confidence=0.8)
        await _create_mem(session_factory, user_id, "I do enjoy meetings at home", confidence=0.8)
        count = await evo_service.detect_contradictions(user_id)
        assert count > 0

    @pytest.mark.asyncio
    async def test_contradiction_weakens_both(self, evo_service, user_id, session_factory):
        m1 = await _create_mem(session_factory, user_id, "I do not believe in failure at all", confidence=0.8)
        await _create_mem(session_factory, user_id, "I do believe in failure at times", confidence=0.8)
        count = await evo_service.detect_contradictions(user_id)
        assert count > 0
        h1 = await evo_service.get_evolution_history(m1)
        weaken_events = [r for r in h1 if r.evolution_type == EvolutionType.CONFIDENCE_UPDATED]
        assert len(weaken_events) >= 1
        assert weaken_events[-1].new_confidence is not None
        assert weaken_events[-1].new_confidence < 0.8

    @pytest.mark.asyncio
    async def test_contradiction_never_deletes(self, evo_service, user_id, session_factory):
        m1 = await _create_mem(session_factory, user_id, "I do not believe in giving up at work", confidence=0.8)
        m2 = await _create_mem(session_factory, user_id, "I do believe in giving up at work", confidence=0.8)
        await evo_service.detect_contradictions(user_id)
        snap1 = await evo_service._get_snapshot(m1)
        snap2 = await evo_service._get_snapshot(m2)
        assert snap1 is not None and snap1.status == "active"
        assert snap2 is not None and snap2.status == "active"

    @pytest.mark.asyncio
    async def test_contradiction_creates_lineage(self, evo_service, user_id, session_factory):
        m1 = await _create_mem(session_factory, user_id, "I do not enjoy being alone at home", confidence=0.7)
        await _create_mem(session_factory, user_id, "I do enjoy being alone at home", confidence=0.7)
        await evo_service.detect_contradictions(user_id)
        descendants = await evo_service.get_descendants(m1)
        contradiction_links = [d for d in descendants if d.relation == "contradicts"]
        assert len(contradiction_links) == 1

    @pytest.mark.asyncio
    async def test_contradiction_confidence_never_negative(self, evo_service, user_id, session_factory):
        m1 = await _create_mem(session_factory, user_id, "I do not believe in failure at all", confidence=0.10)
        await _create_mem(session_factory, user_id, "I do believe in failure at times", confidence=0.10)
        await evo_service.detect_contradictions(user_id)
        snap1 = await evo_service._get_snapshot(m1)
        assert snap1 is not None and snap1.confidence >= evo_service._config.weaken_min_confidence


# ════════════════════════════════════════════════════════════════════════
# Strengthening tests
# ════════════════════════════════════════════════════════════════════════

class TestStrengthening:
    @pytest.mark.asyncio
    async def test_strengthen_increases_confidence(self, evo_service, user_id, session_factory):
        mid = await _create_mem(session_factory, user_id, "Core belief", confidence=0.5)
        await evo_service.strengthen_memory(mid, user_id)
        snap = await evo_service._get_snapshot(mid)
        assert snap is not None and snap.confidence == 0.6

    @pytest.mark.asyncio
    async def test_strengthen_caps_at_max(self, evo_service, user_id, session_factory):
        mid = await _create_mem(session_factory, user_id, "Near max", confidence=0.98)
        await evo_service.strengthen_memory(mid, user_id)
        snap = await evo_service._get_snapshot(mid)
        assert snap is not None and snap.confidence == 1.0

    @pytest.mark.asyncio
    async def test_strengthen_idempotent_at_ceiling(self, evo_service, user_id, session_factory):
        mid = await _create_mem(session_factory, user_id, "At ceiling", confidence=1.0)
        record = await evo_service.strengthen_memory(mid, user_id)
        assert record.detail == "Already at max confidence"

    @pytest.mark.asyncio
    async def test_strengthen_creates_evolution_record(self, evo_service, user_id, session_factory):
        mid = await _create_mem(session_factory, user_id, "Recorded")
        await evo_service.strengthen_memory(mid, user_id)
        history = await evo_service.get_evolution_history(mid)
        strengthened = [r for r in history if r.evolution_type == EvolutionType.CONFIDENCE_UPDATED]
        assert len(strengthened) >= 1
        assert strengthened[-1].old_confidence is not None
        assert strengthened[-1].new_confidence is not None
        assert strengthened[-1].new_confidence > strengthened[-1].old_confidence

    @pytest.mark.asyncio
    async def test_batch_strengthening(self, evo_service, user_id, session_factory):
        await _create_mem(session_factory, user_id, "Recent A", confidence=0.5, created_days_ago=5)
        await _create_mem(session_factory, user_id, "Recent B", confidence=0.5, created_days_ago=5)
        result = await evo_service.run_consolidation(user_id)
        assert result.strengthened > 0


# ════════════════════════════════════════════════════════════════════════
# Weakening tests
# ════════════════════════════════════════════════════════════════════════

class TestWeakening:
    @pytest.mark.asyncio
    async def test_weaken_decreases_confidence(self, evo_service, user_id, session_factory):
        mid = await _create_mem(session_factory, user_id, "Old belief", confidence=0.7)
        await evo_service.weaken_confidence(mid, user_id)
        snap = await evo_service._get_snapshot(mid)
        assert snap is not None
        assert abs(snap.confidence - 0.65) < 0.01

    @pytest.mark.asyncio
    async def test_weaken_never_negative(self, evo_service, user_id, session_factory):
        mid = await _create_mem(session_factory, user_id, "Low conf", confidence=0.06)
        await evo_service.weaken_confidence(mid, user_id)
        snap = await evo_service._get_snapshot(mid)
        assert snap is not None and snap.confidence >= 0.05

    @pytest.mark.asyncio
    async def test_weaken_idempotent_at_floor(self, evo_service, user_id, session_factory):
        mid = await _create_mem(session_factory, user_id, "At floor", confidence=0.05)
        record = await evo_service.weaken_confidence(mid, user_id)
        assert record.detail == "Already at min confidence"

    @pytest.mark.asyncio
    async def test_batch_weakening_for_stale(self, evo_service, user_id, session_factory):
        await _create_mem(session_factory, user_id, "Stale fact", confidence=0.6,
                         created_days_ago=100, updated_days_ago=100)
        result = await evo_service.run_consolidation(user_id)
        assert result.weakened > 0

    @pytest.mark.asyncio
    async def test_weaken_records_reason(self, evo_service, user_id, session_factory):
        mid = await _create_mem(session_factory, user_id, "Contradicted")
        await evo_service.weaken_confidence(mid, user_id, reason=EvolutionReason.CONTRADICTION,
                                            detail="User corrected this")
        history = await evo_service.get_evolution_history(mid)
        assert any(r.detail == "User corrected this" for r in history)


# ════════════════════════════════════════════════════════════════════════
# Confidence evolution tests
# ════════════════════════════════════════════════════════════════════════

class TestConfidenceEvolution:
    @pytest.mark.asyncio
    async def test_evolve_confidence(self, evo_service, user_id, session_factory):
        mid = await _create_mem(session_factory, user_id, "Fact", confidence=0.5)
        await evo_service.evolve_confidence(mid, user_id, 0.8, reason=EvolutionReason.MANUAL)
        snap = await evo_service._get_snapshot(mid)
        assert snap is not None and snap.confidence == 0.8

    @pytest.mark.asyncio
    async def test_confidence_history_append_only(self, evo_service, user_id, session_factory):
        mid = await _create_mem(session_factory, user_id, "Evolving fact")
        await evo_service.evolve_confidence(mid, user_id, 0.6)
        await evo_service.evolve_confidence(mid, user_id, 0.7)
        await evo_service.evolve_confidence(mid, user_id, 0.8)
        history = await evo_service.get_evolution_history(mid)
        confidence_events = [r for r in history if r.evolution_type == EvolutionType.CONFIDENCE_UPDATED]
        assert len(confidence_events) >= 3
        values = [r.new_confidence for r in confidence_events if r.new_confidence is not None]
        assert values == sorted(values)

    @pytest.mark.asyncio
    async def test_confidence_clamped(self, evo_service, user_id, session_factory):
        mid = await _create_mem(session_factory, user_id, "Clamped")
        await evo_service.evolve_confidence(mid, user_id, 5.0)
        snap = await evo_service._get_snapshot(mid)
        assert snap is not None and snap.confidence == 1.0

    @pytest.mark.asyncio
    async def test_every_change_creates_record(self, evo_service, user_id, session_factory):
        mid = await _create_mem(session_factory, user_id, "Every change")
        await evo_service.evolve_confidence(mid, user_id, 0.6)
        await evo_service.evolve_confidence(mid, user_id, 0.65)
        history = await evo_service.get_evolution_history(mid)
        assert len(history) >= 2


# ════════════════════════════════════════════════════════════════════════
# Importance evolution tests
# ════════════════════════════════════════════════════════════════════════

class TestImportanceEvolution:
    @pytest.mark.asyncio
    async def test_boost_importance(self, evo_service, user_id, session_factory):
        mid = await _create_mem(session_factory, user_id, "Important")
        await evo_service.boost_importance(mid, user_id)
        history = await evo_service.get_evolution_history(mid)
        imp_events = [r for r in history if r.evolution_type == EvolutionType.IMPORTANCE_UPDATED]
        assert len(imp_events) == 1
        assert imp_events[0].new_importance is not None
        assert imp_events[0].new_importance > (imp_events[0].old_importance or 0)

    @pytest.mark.asyncio
    async def test_decay_importance(self, evo_service, user_id, session_factory):
        mid = await _create_mem(session_factory, user_id, "Decaying")
        await evo_service.decay_importance(mid, user_id)
        history = await evo_service.get_evolution_history(mid)
        imp_events = [r for r in history if r.evolution_type == EvolutionType.IMPORTANCE_UPDATED]
        assert len(imp_events) == 1
        assert imp_events[0].new_importance is not None
        assert imp_events[0].new_importance < (imp_events[0].old_importance or 1.0)

    @pytest.mark.asyncio
    async def test_importance_independent_from_confidence(self, evo_service, user_id, session_factory):
        mid = await _create_mem(session_factory, user_id, "Independent")
        await evo_service.boost_importance(mid, user_id)
        snap = await evo_service._get_snapshot(mid)
        assert snap is not None
        assert snap.confidence == 0.5


# ════════════════════════════════════════════════════════════════════════
# Lineage preservation tests
# ════════════════════════════════════════════════════════════════════════

class TestLineagePreservation:
    @pytest.mark.asyncio
    async def test_merge_lineage_chain(self, evo_service, user_id, session_factory):
        m1 = await _create_mem(session_factory, user_id, "A original")
        m2 = await _create_mem(session_factory, user_id, "A similar")
        m3 = await _create_mem(session_factory, user_id, "B different")
        merged = await evo_service.merge_memories([m1, m2], user_id)
        await evo_service.add_lineage(m3, merged, "superseded_by")

        full = await evo_service.get_full_lineage(merged)
        assert len(full["ancestors"]) == 3

    @pytest.mark.asyncio
    async def test_contradiction_link_preserved(self, evo_service, user_id, session_factory):
        m1 = await _create_mem(session_factory, user_id, "I do not value money at all", confidence=0.8)
        await _create_mem(session_factory, user_id, "I do value money above all", confidence=0.8)
        await evo_service.detect_contradictions(user_id)
        descendants = await evo_service.get_descendants(m1)
        assert any(d.relation == "contradicts" for d in descendants)


# ════════════════════════════════════════════════════════════════════════
# Idempotency tests
# ════════════════════════════════════════════════════════════════════════

class TestIdempotency:
    @pytest.mark.asyncio
    async def test_merge_idempotent(self, evo_service, user_id, session_factory):
        m1 = await _create_mem(session_factory, user_id, "Idempotent A fact")
        m2 = await _create_mem(session_factory, user_id, "Idempotent A belief")
        id1 = await evo_service.merge_memories([m1, m2], user_id)
        id2 = await evo_service.merge_memories([m1, m2], user_id)
        assert id1 == id2

    @pytest.mark.asyncio
    async def test_consolidation_idempotent(self, evo_service, user_id, session_factory):
        await _create_mem(session_factory, user_id, "Already strong fact", confidence=0.95,
                         created_days_ago=5)
        await evo_service.run_consolidation(user_id)
        r2 = await evo_service.run_consolidation(user_id)
        assert r2.strengthened == 0

    @pytest.mark.asyncio
    async def test_lineage_idempotent(self, evo_service, user_id, session_factory):
        m1 = await _create_mem(session_factory, user_id, "Parent for idempotent")
        m2 = await _create_mem(session_factory, user_id, "Child for idempotent")
        l1 = await evo_service.add_lineage(m1, m2, "superseded_by")
        l2 = await evo_service.add_lineage(m1, m2, "superseded_by")
        assert l1.id == l2.id


# ════════════════════════════════════════════════════════════════════════
# Consolidation pipeline tests
# ════════════════════════════════════════════════════════════════════════

class TestConsolidationPipeline:
    @pytest.mark.asyncio
    async def test_full_consolidation(self, evo_service, user_id, session_factory):
        await _create_mem(session_factory, user_id, "Merged A about growth", confidence=0.5, created_days_ago=5)
        await _create_mem(session_factory, user_id, "Merged A about development", confidence=0.6, created_days_ago=5)
        await _create_mem(session_factory, user_id, "Stale old fact", confidence=0.6, created_days_ago=100, updated_days_ago=100)
        result = await evo_service.run_consolidation(user_id)
        assert result.merges > 0 or result.strengthened > 0 or result.weakened > 0
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_consolidation_observability(self, evo_service, user_id, session_factory):
        await _create_mem(session_factory, user_id, "Observable fact", confidence=0.5, created_days_ago=5)
        await evo_service.run_consolidation(user_id)
        metrics = await evo_service.get_metrics(user_id)
        assert metrics.total_records > 0


# ════════════════════════════════════════════════════════════════════════
# Concurrent evolution tests
# ════════════════════════════════════════════════════════════════════════

class TestConcurrentEvolution:
    @pytest.mark.asyncio
    async def test_parallel_strengthening(self, evo_service, user_id, session_factory):
        mid = await _create_mem(session_factory, user_id, "Concurrent target", confidence=0.5)
        tasks = [evo_service.strengthen_memory(mid, user_id) for _ in range(5)]
        await asyncio.gather(*tasks)
        snap = await evo_service._get_snapshot(mid)
        assert snap is not None and snap.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_parallel_different_memories(self, evo_service, user_id, session_factory):
        ids = [await _create_mem(session_factory, user_id, f"Parallel mem {i}", confidence=0.5) for i in range(5)]
        tasks = [evo_service.strengthen_memory(mid, user_id) for mid in ids]
        await asyncio.gather(*tasks)
        for mid in ids:
            snap = await evo_service._get_snapshot(mid)
            assert snap is not None and snap.confidence >= 0.5
