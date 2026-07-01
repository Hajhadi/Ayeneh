"""Comprehensive tests for the Deliberative Reasoning Engine."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ayeneh.infrastructure.persistence.base import Base
from ayeneh.infrastructure.persistence.models.user import UserModel
from ayeneh.infrastructure.persistence.unit_of_work import UnitOfWork
from ayeneh.reasoning.conflicts import ConflictDetector
from ayeneh.reasoning.engine import ReasoningEngine
from ayeneh.reasoning.evidence import EvidenceCollector
from ayeneh.reasoning.hypotheses import HypothesisGenerator
from ayeneh.reasoning.observability import ReasoningMetrics
from ayeneh.reasoning.types import (
    Conflict,
    Evidence,
    EvidenceSource,
    Hypothesis,
    ReasoningSession,
    ReasoningStage,
    ReasoningSummary,
)
from ayeneh.reasoning.uncertainty import UncertaintyEstimator
from ayeneh.goal.service import GoalService


def _utcnow() -> datetime:
    return datetime.now(UTC)


# ── Fixtures ──

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
def goal_service(uow_factory):
    return GoalService(uow_factory=uow_factory)


@pytest_asyncio.fixture
def reasoning_engine(goal_service):
    return ReasoningEngine(goal_service=goal_service)


import uuid


# ════════════════════════════════════════════════════════════════════════
# Types tests
# ════════════════════════════════════════════════════════════════════════

class TestReasoningTypes:
    def test_evidence_creation(self):
        e = Evidence(source_type="memory", content="test", confidence=0.7)
        assert e.source_type == "memory"
        assert e.confidence == 0.7

    def test_hypothesis_creation(self):
        h = Hypothesis(claim="test claim", confidence=0.6)
        assert h.claim == "test claim"
        assert len(h.supporting_evidence) == 0

    def test_conflict_creation(self):
        c = Conflict(conflict_type="contradiction", severity=0.8)
        assert c.severity == 0.8

    def test_reasoning_session(self):
        session = ReasoningSession(user_id="u1", query="test")
        session.add_step("stage1", "step description")
        assert len(session.reasoning_steps) == 1
        assert session.duration_ms >= 0

    def test_reasoning_summary(self):
        s = ReasoningSummary(objective="test", confidence=0.8)
        assert s.confidence == 0.8
        assert s.objective == "test"

    def test_reasoning_stage_values(self):
        assert ReasoningStage.UNDERSTAND == "understand_request"
        assert ReasoningStage.CONFIDENCE == "estimate_confidence"
        assert ReasoningStage.SUMMARY == "build_reasoning_summary"


# ════════════════════════════════════════════════════════════════════════
# Evidence collector tests
# ════════════════════════════════════════════════════════════════════════

class TestEvidenceCollector:
    @pytest.mark.asyncio
    async def test_collect_goals(self, goal_service, user_id):
        g = await goal_service.create_goal(user_id, "Learn Python")
        await goal_service.activate_goal(g.id)
        collector = EvidenceCollector(goal_service=goal_service)
        evidence = await collector._collect_goals(user_id)
        assert len(evidence) == 1
        assert evidence[0].source_type == EvidenceSource.GOAL

    @pytest.mark.asyncio
    async def test_collect_all(self, goal_service, user_id):
        g = await goal_service.create_goal(user_id, "Goal")
        await goal_service.activate_goal(g.id)
        collector = EvidenceCollector(goal_service=goal_service)
        evidence = await collector.collect_all(user_id, "test query")
        assert len(evidence) >= 1

    @pytest.mark.asyncio
    async def test_collect_without_goal_service(self):
        collector = EvidenceCollector()
        evidence = await collector.collect_all("u1", "query")
        assert len(evidence) == 0


# ════════════════════════════════════════════════════════════════════════
# Conflict detection tests
# ════════════════════════════════════════════════════════════════════════

class TestConflictDetector:
    def test_detects_negation_conflict(self):
        detector = ConflictDetector()
        evidence = [
            Evidence(source_type="memory", content="I always avoid conflict at work"),
            Evidence(source_type="memory", content="I never avoid conflict at work"),
        ]
        conflicts = detector.detect(evidence)
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == "contradiction"

    def test_no_conflict_similar_statements(self):
        detector = ConflictDetector()
        evidence = [
            Evidence(source_type="memory", content="I enjoy reading books"),
            Evidence(source_type="memory", content="I enjoy reading novels"),
        ]
        conflicts = detector.detect(evidence)
        assert len(conflicts) == 0

    def test_cross_source_conflict(self):
        detector = ConflictDetector()
        evidence = [
            Evidence(source_type="memory", content="I do not believe in failure"),
            Evidence(source_type="goal", content="I do believe in learning from failure"),
        ]
        conflicts = detector.detect(evidence)
        assert len(conflicts) >= 1

    def test_empty_evidence(self):
        detector = ConflictDetector()
        assert detector.detect([]) == []


# ════════════════════════════════════════════════════════════════════════
# Hypothesis generator tests
# ════════════════════════════════════════════════════════════════════════

class TestHypothesisGenerator:
    def test_generate_hypotheses(self):
        generator = HypothesisGenerator()
        evidence = [
            Evidence(source_type="memory", content="User likes Python", confidence=0.8),
            Evidence(source_type="goal", content="Learn Python", confidence=0.9),
        ]
        hypotheses = generator.generate(evidence, "Understanding Python learning")
        assert len(hypotheses) >= 2
        assert all(h.claim for h in hypotheses)

    def test_generate_empty_evidence(self):
        generator = HypothesisGenerator()
        hypotheses = generator.generate([], "test")
        assert len(hypotheses) == 1
        assert "Limited evidence" in hypotheses[0].claim

    def test_generate_assigns_evidence(self):
        generator = HypothesisGenerator()
        evidence = [
            Evidence(source_type="memory", content="A", confidence=0.8),
            Evidence(source_type="memory", content="B", confidence=0.3),
        ]
        hypotheses = generator.generate(evidence, "test")
        has_supporting = any(len(h.supporting_evidence) > 0 for h in hypotheses)
        assert has_supporting


# ════════════════════════════════════════════════════════════════════════
# Uncertainty estimator tests
# ════════════════════════════════════════════════════════════════════════

class TestUncertaintyEstimator:
    def test_high_confidence(self):
        estimator = UncertaintyEstimator()
        evidence = [Evidence(source_type="memory", content="A", confidence=0.9) for _ in range(5)]
        confidence, reasons = estimator.estimate(evidence, [], 1, {"memory", "goal"})
        assert confidence > 0.5

    def test_low_confidence(self):
        estimator = UncertaintyEstimator()
        confidence, reasons = estimator.estimate([], [], 0)
        assert confidence == 0.1
        assert "No evidence" in reasons[0]

    def test_conflicts_lower_confidence(self):
        estimator = UncertaintyEstimator()
        evidence = [Evidence(source_type="memory", content="A", confidence=0.8)]
        conflicts = [Conflict(severity=0.8)]
        c_no = estimator.estimate(evidence, [], 0)[0]
        c_yes = estimator.estimate(evidence, conflicts, 0)[0]
        assert c_yes < c_no

    def test_more_alternatives_lower_confidence(self):
        estimator = UncertaintyEstimator()
        evidence = [Evidence(source_type="memory", content="A", confidence=0.8)]
        c1, _ = estimator.estimate(evidence, [], 1)
        c2, _ = estimator.estimate(evidence, [], 5)
        assert c2 <= c1


# ════════════════════════════════════════════════════════════════════════
# ReasoningEngine tests
# ════════════════════════════════════════════════════════════════════════

class TestReasoningEngine:
    @pytest.mark.asyncio
    async def test_basic_reasoning(self, reasoning_engine, user_id):
        session = await reasoning_engine.reason(user_id, "How is my learning going?")
        assert session.objective
        assert len(session.reasoning_steps) >= 4
        assert 0 <= session.summary.confidence <= 1

    @pytest.mark.asyncio
    async def test_reasoning_with_goals(self, reasoning_engine, goal_service, user_id):
        g = await goal_service.create_goal(user_id, "Learn Python", importance=0.9)
        await goal_service.activate_goal(g.id)
        session = await reasoning_engine.reason(user_id, "Python progress")
        assert len(session.evidence) >= 1

    @pytest.mark.asyncio
    async def test_reasoning_detects_conflicts(self, reasoning_engine, user_id):
        session = await reasoning_engine.reason(
            user_id, "test",
            context={"evidence_override": [
                Evidence(source_type="memory", content="I always avoid conflict at work"),
                Evidence(source_type="goal", content="I never avoid conflict at work"),
            ]},
        )
        assert session.conflicts is not None

    @pytest.mark.asyncio
    async def test_reasoning_summary_structure(self, reasoning_engine, user_id):
        session = await reasoning_engine.reason(user_id, "test query")
        summary = session.summary
        assert summary.objective
        assert len(summary.reasoning_path) >= 3
        assert isinstance(summary.confidence, float)
        assert isinstance(summary.limitations, list)

    @pytest.mark.asyncio
    async def test_empty_evidence_low_confidence(self, reasoning_engine, user_id):
        session = await reasoning_engine.reason(user_id, "test")
        assert session.summary.confidence < 0.5

    @pytest.mark.asyncio
    async def test_reasoning_stages_executed(self, reasoning_engine, user_id):
        session = await reasoning_engine.reason(user_id, "test")
        stages = [s.stage for s in session.reasoning_steps]
        assert ReasoningStage.UNDERSTAND in stages
        assert ReasoningStage.EVIDENCE in stages
        assert ReasoningStage.HYPOTHESIS in stages
        assert ReasoningStage.CONFLICTS in stages
        assert ReasoningStage.CONFIDENCE in stages
        assert ReasoningStage.SUMMARY in stages


# ════════════════════════════════════════════════════════════════════════
# Observability tests
# ════════════════════════════════════════════════════════════════════════

class TestReasoningObservability:
    def test_record_session(self):
        metrics = ReasoningMetrics()
        metrics.record_session(100.0, 0.7, 10, 3, 1, 2)
        assert metrics.total_sessions == 1
        assert metrics.total_evidence_evaluated == 10
        assert metrics.avg_confidence == 0.7

    def test_record_failure(self):
        metrics = ReasoningMetrics()
        metrics.record_failure()
        assert metrics.reasoning_failures == 1

    def test_summary(self):
        metrics = ReasoningMetrics()
        metrics.record_session(50.0, 0.8, 5, 2, 0, 1)
        s = metrics.get_summary()
        assert s["total_sessions"] == 1
        assert s["avg_confidence"] == 0.8

    def test_prometheus_export(self):
        metrics = ReasoningMetrics()
        metrics.record_session(100.0, 0.75, 8, 3, 0, 2)
        text = metrics.export_prometheus_text()
        assert "ayeneh_reasoning_sessions_total 1" in text


# ════════════════════════════════════════════════════════════════════════
# Concurrency tests
# ════════════════════════════════════════════════════════════════════════

class TestReasoningConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_reasoning_sessions(self, reasoning_engine, goal_service, user_id):
        await goal_service.create_goal(user_id, "Goal A")
        await goal_service.create_goal(user_id, "Goal B")

        async def reason():
            return await reasoning_engine.reason(user_id, "test query")

        sessions = await asyncio.gather(*[reason() for _ in range(5)])
        assert len(sessions) == 5
        assert all(s.summary.confidence >= 0 for s in sessions)

    @pytest.mark.asyncio
    async def test_concurrent_evidence_collection(self, reasoning_engine, goal_service, user_id):
        g = await goal_service.create_goal(user_id, "Goal")
        await goal_service.activate_goal(g.id)
        collector = reasoning_engine._evidence_collector

        async def collect():
            return await collector.collect_all(user_id, "query")

        results = await asyncio.gather(*[collect() for _ in range(3)])
        assert all(len(r) >= 1 for r in results)
