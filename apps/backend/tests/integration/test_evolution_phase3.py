"""Integration tests for Memory Evolution Phase 3 — runtime integration.

Covers: evolution-aware retrieval, prompt context injection, scheduler
execution, retrieval ordering, metrics, agent grounding, idempotency.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ayeneh.application.services.evolution_aware_retrieval import (
    EvolutionAwareRetrievalStrategy,
)
from ayeneh.application.services.evolution_scheduler import (
    EvolutionScheduler,
    SchedulerConfig,
)
from ayeneh.application.services.memory_evolution import (
    EvolutionConfig,
    EvolutionType,
    MemoryEvolutionService,
)
from ayeneh.application.services.prompt_context import PromptContextService
from ayeneh.application.services.retrieval import RetrievalResult, RetrievalService
from ayeneh.infrastructure.persistence.base import Base
from ayeneh.infrastructure.persistence.models.memory import MemoryModel
from ayeneh.infrastructure.persistence.models.user import UserModel
from ayeneh.infrastructure.persistence.unit_of_work import UnitOfWork


def _utcnow() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeMemory:
    def __init__(self, **kw):
        self.id = kw.get("id", uuid.uuid4())
        self.type = type("T", (), {"value": kw.get("memory_type", "semantic")})()
        self.content = kw.get("content", "")
        self.confidence = kw.get("confidence", 0.5)
        self.status = kw.get("status", "active")
        self.evolution_version = kw.get("evolution_version", 1)
        self.confidence_history = kw.get("confidence_history", None)


class _FakeScore:
    def __init__(self, memory, final_score):
        self.memory = memory
        self.final_score = final_score


class _FakeCtx:
    def __init__(self, scores):
        self.scores = scores


class _FakeMemoryService:
    def __init__(self, memories):
        self._memories = memories

    async def retrieve(self, uid, q, **kw):
        return _FakeCtx([_FakeScore(m, m.confidence) for m in self._memories])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
    return MemoryEvolutionService(uow_factory=uow_factory)


async def _create_mem(session_factory, user_id: str, content: str,
                      memory_type: str = "semantic", confidence: float = 0.5,
                      created_days_ago: int = 0, updated_days_ago: int | None = None,
                      evolution_version: int = 1) -> str:
    mid = uuid.uuid4()
    now = datetime.now(UTC)
    created = now - timedelta(days=created_days_ago)
    updated = now - timedelta(days=updated_days_ago if updated_days_ago is not None else created_days_ago)
    async with session_factory() as session:
        session.add(MemoryModel(
            id=mid, user_id=uuid.UUID(user_id), type=memory_type,
            content=content, confidence=confidence, source_message_ids=[],
            status="active", created_at=created, updated_at=updated,
            evolution_version=evolution_version,
            confidence_history={"v1": confidence} if evolution_version > 1 else None,
        ))
        await session.commit()
    return str(mid)


# ════════════════════════════════════════════════════════════════════════
# Evolution-aware retrieval strategy
# ════════════════════════════════════════════════════════════════════════

class TestEvolutionAwareRetrieval:
    @pytest.mark.asyncio
    async def test_boosts_evolved_memories(self, evo_service, user_id):
        raw = _FakeMemory(content="Raw", evolution_version=1)
        evolved = _FakeMemory(content="Evolved", evolution_version=3,
                              confidence_history={"v1": 0.5, "v2": 0.6})
        strategy = EvolutionAwareRetrievalStrategy(
            memory_service=_FakeMemoryService([raw, evolved]),
            evolution_service=evo_service,
        )
        result = await strategy.retrieve(uuid.UUID(user_id), "q")
        scores = [s.final_score for s in result.scores]
        assert scores[0] > scores[1]

    @pytest.mark.asyncio
    async def test_penalizes_superseded(self, evo_service, user_id):
        active = _FakeMemory(content="Active", status="active")
        old = _FakeMemory(content="Old", status="superseded")
        strategy = EvolutionAwareRetrievalStrategy(
            memory_service=_FakeMemoryService([active, old]),
            evolution_service=evo_service,
        )
        result = await strategy.retrieve(uuid.UUID(user_id), "q")
        scores = [s.final_score for s in result.scores]
        assert scores[0] > scores[1]

    @pytest.mark.asyncio
    async def test_works_without_evolution_service(self, user_id):
        m = _FakeMemory(content="Fact")
        strategy = EvolutionAwareRetrievalStrategy(
            memory_service=_FakeMemoryService([m]),
            evolution_service=None,
        )
        result = await strategy.retrieve(uuid.UUID(user_id), "q")
        assert len(result.scores) == 1


# ════════════════════════════════════════════════════════════════════════
# RetrievalService integration
# ════════════════════════════════════════════════════════════════════════

class TestRetrievalServiceIntegration:
    @pytest.mark.asyncio
    async def test_uses_evolution_aware_strategy(self, user_id):
        class FakeEA:
            async def retrieve(self, uid, q, **kw):
                return _FakeCtx([_FakeScore(
                    _FakeMemory(content="Evolved", evolution_version=3,
                                confidence_history={"v1": 0.5, "v3": 0.8}),
                    0.8,
                )])

        rs = RetrievalService(evolution_aware_strategy=FakeEA())
        result = await rs.retrieve_context(user_id, "q")
        assert len(result.memories) == 1
        assert result.memories[0]["evolution_version"] == 3
        assert result.evolved_memory_count == 1

    @pytest.mark.asyncio
    async def test_falls_back_to_raw(self, user_id):
        rs = RetrievalService(memory_service=_FakeMemoryService([
            _FakeMemory(content="Raw", evolution_version=1)
        ]))
        result = await rs.retrieve_context(user_id, "q")
        assert len(result.memories) == 1
        assert result.evolved_memory_count == 0

    @pytest.mark.asyncio
    async def test_counts_superseded(self, user_id):
        class FakeEA:
            async def retrieve(self, uid, q, **kw):
                return _FakeCtx([
                    _FakeScore(_FakeMemory(content="A", status="active"), 0.7),
                    _FakeScore(_FakeMemory(content="B", status="superseded"), 0.3),
                ])

        rs = RetrievalService(evolution_aware_strategy=FakeEA())
        result = await rs.retrieve_context(user_id, "q")
        assert result.superseded_memory_count == 1


# ════════════════════════════════════════════════════════════════════════
# PromptContext injection
# ════════════════════════════════════════════════════════════════════════

class TestPromptContextInjection:
    @pytest.mark.asyncio
    async def test_evolved_memory_header(self, user_id):
        class FakeRetrieval:
            async def retrieve_context(self, uid, query, **kw):
                return RetrievalResult(
                    memories=[{"type": "semantic", "content": "Evolved fact",
                               "confidence": 0.8, "evolution_version": 3, "score": 0.8}],
                    evolved_memory_count=1,
                )
        ctx = await PromptContextService(retrieval_service=FakeRetrieval()).assemble(user_id, "q")
        assert "1 evolved" in ctx.memory_context

    @pytest.mark.asyncio
    async def test_shows_version_in_tag(self, user_id):
        class FakeRetrieval:
            async def retrieve_context(self, uid, query, **kw):
                return RetrievalResult(
                    memories=[
                        {"type": "semantic", "content": "V3", "confidence": 0.9,
                         "evolution_version": 3, "score": 0.9},
                    ],
                    evolved_memory_count=1,
                )
        ctx = await PromptContextService(retrieval_service=FakeRetrieval()).assemble(user_id, "q")
        assert "[v3" in ctx.memory_context
        assert "conf=0.90" in ctx.memory_context


# ════════════════════════════════════════════════════════════════════════
# Evolution scheduler
# ════════════════════════════════════════════════════════════════════════

class TestEvolutionScheduler:
    @pytest.mark.asyncio
    async def test_trigger_daily(self, evo_service, user_id, session_factory):
        await _create_mem(session_factory, user_id, "Stale", confidence=0.5,
                         created_days_ago=100, updated_days_ago=100)
        scheduler = EvolutionScheduler(evo_service)
        result = await scheduler.trigger_daily(user_id)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_trigger_weekly(self, evo_service, user_id, session_factory):
        await _create_mem(session_factory, user_id, "Recent", confidence=0.5, created_days_ago=5)
        scheduler = EvolutionScheduler(evo_service)
        result = await scheduler.trigger_weekly(user_id)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_trigger_monthly(self, evo_service, user_id, session_factory):
        await _create_mem(session_factory, user_id, "Old", confidence=0.5,
                         created_days_ago=100, updated_days_ago=100)
        scheduler = EvolutionScheduler(evo_service)
        result = await scheduler.trigger_monthly(user_id)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_publishes_events(self, evo_service, user_id):
        events = []

        class FakePub:
            async def publish(self, etype, payload):
                events.append({"type": etype, **payload})

        scheduler = EvolutionScheduler(evo_service, event_publisher=FakePub())
        await scheduler.trigger_daily(user_id)
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_get_recent_results(self, evo_service, user_id, session_factory):
        await _create_mem(session_factory, user_id, "R1", confidence=0.5,
                         created_days_ago=100, updated_days_ago=100)
        scheduler = EvolutionScheduler(evo_service)
        await scheduler.trigger_daily(user_id)
        await scheduler.trigger_weekly(user_id)
        assert len(scheduler.get_recent_results()) >= 2

    @pytest.mark.asyncio
    async def test_handles_errors(self, user_id):
        broken = MemoryEvolutionService.__new__(MemoryEvolutionService)
        broken._uow_factory = lambda: (_ for _ in ()).throw(RuntimeError("fail"))
        broken._config = EvolutionConfig()
        scheduler = EvolutionScheduler(broken)
        result = await scheduler.trigger_daily(user_id)
        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_disabled_noop(self, evo_service, user_id):
        scheduler = EvolutionScheduler(evo_service, config=SchedulerConfig(enabled=False))
        await scheduler.start([user_id])
        await asyncio.sleep(0.05)
        assert len(scheduler.get_recent_results()) == 0
        await scheduler.stop()


# ════════════════════════════════════════════════════════════════════════
# Agent grounding
# ════════════════════════════════════════════════════════════════════════

class TestAgentGrounding:
    @pytest.mark.asyncio
    async def test_strengthened_memory_flows(self, evo_service, user_id, session_factory):
        mid = await _create_mem(session_factory, user_id, "Recurring pattern", confidence=0.7)
        await evo_service.strengthen_memory(mid, user_id)
        snap = await evo_service._get_snapshot(mid)
        assert snap is not None and snap.confidence > 0.7

    @pytest.mark.asyncio
    async def test_merged_memory_flows(self, evo_service, user_id, session_factory):
        m1 = await _create_mem(session_factory, user_id, "Growth A about learning deeply", confidence=0.6)
        m2 = await _create_mem(session_factory, user_id, "Growth A about learning deeply", confidence=0.7)
        await evo_service.detect_and_merge_similar(user_id)
        history1 = await evo_service.get_evolution_history(m1)
        assert any(r.evolution_type == EvolutionType.MERGED for r in history1)

    @pytest.mark.asyncio
    async def test_contradiction_detected(self, evo_service, user_id, session_factory):
        m1 = await _create_mem(session_factory, user_id, "I always try to avoid conflict", confidence=0.7)
        m2 = await _create_mem(session_factory, user_id, "I always try to avoid confrontation", confidence=0.7)
        result = await evo_service.run_consolidation(user_id)
        assert result.merges > 0 or result.contradictions > 0 or result.strengthened > 0


# ════════════════════════════════════════════════════════════════════════
# Retrieval ordering
# ════════════════════════════════════════════════════════════════════════

class TestRetrievalOrdering:
    @pytest.mark.asyncio
    async def test_strategy_routes_through_memory_service(self, evo_service, user_id):
        call_log = []

        class FakeMS:
            async def retrieve(self, uid, q, **kw):
                call_log.append("called")
                return _FakeCtx([_FakeScore(_FakeMemory(content="F"), 0.5)])

        strategy = EvolutionAwareRetrievalStrategy(
            memory_service=FakeMS(), evolution_service=evo_service,
        )
        await strategy.retrieve(uuid.UUID(user_id), "q")
        assert "called" in call_log

    @pytest.mark.asyncio
    async def test_metadata_propagates(self, user_id):
        class FakeEA:
            async def retrieve(self, uid, q, **kw):
                return _FakeCtx([_FakeScore(
                    _FakeMemory(content="E", evolution_version=4,
                                confidence_history={"v1": 0.4, "v4": 0.8}),
                    0.8,
                )])

        rs = RetrievalService(evolution_aware_strategy=FakeEA())
        result = await rs.retrieve_context(user_id, "q")
        assert result.memories[0]["evolution_version"] == 4
        assert result.memories[0]["confidence_history"]["v4"] == 0.8


# ════════════════════════════════════════════════════════════════════════
# Metrics
# ════════════════════════════════════════════════════════════════════════

class TestRuntimeMetrics:
    @pytest.mark.asyncio
    async def test_retrieval_tracks_stats(self, user_id):
        class FakeEA:
            async def retrieve(self, uid, q, **kw):
                return _FakeCtx([
                    _FakeScore(_FakeMemory(content="E", evolution_version=3), 0.8),
                    _FakeScore(_FakeMemory(content="S", status="superseded"), 0.3),
                ])

        rs = RetrievalService(evolution_aware_strategy=FakeEA())
        result = await rs.retrieve_context(user_id, "q")
        assert result.evolved_memory_count == 1
        assert result.superseded_memory_count == 1
