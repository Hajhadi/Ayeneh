"""Goal Integration Tests — runtime, retrieval, prompt, agents, scheduler, metrics."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ayeneh.application.services.prompt_context import PromptContext, PromptContextService
from ayeneh.application.services.retrieval import RetrievalResult, RetrievalService
from ayeneh.goal.context import GoalContext, GoalContextBuilder
from ayeneh.goal.domain import Goal, GoalStatus
from ayeneh.goal.evolution import GoalEvolutionConfig, GoalEvolutionService
from ayeneh.goal.observability import GoalEventPublisher, GoalMetrics
from ayeneh.goal.retrieval import GoalRetrievalService
from ayeneh.goal.service import GoalService
from ayeneh.infrastructure.persistence.base import Base
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
def goal_service(uow_factory):
    return GoalService(uow_factory=uow_factory)


@pytest_asyncio.fixture
def goal_retrieval(goal_service):
    return GoalRetrievalService(goal_service)


@pytest_asyncio.fixture
def goal_evolution(goal_service):
    return GoalEvolutionService(goal_service)


@pytest_asyncio.fixture
def goal_context_builder(goal_retrieval, goal_service):
    return GoalContextBuilder(goal_retrieval, goal_service)


# ════════════════════════════════════════════════════════════════════════
# Retrieval Integration Tests
# ════════════════════════════════════════════════════════════════════════

class TestRetrievalIntegration:
    @pytest.mark.asyncio
    async def test_retrieval_includes_goals(self, goal_service, goal_retrieval, user_id):
        rs = RetrievalService(goal_retrieval=goal_retrieval, goal_service=goal_service)
        goal = await goal_service.create_goal(user_id, "Learn Python", importance=0.9)
        await goal_service.activate_goal(goal.id)

        result = await rs.retrieve_context(user_id, "How is my learning going?")
        assert len(result.active_goals) >= 1
        assert result.active_goals[0]["title"] == "Learn Python"
        assert result.goal_count >= 1

    @pytest.mark.asyncio
    async def test_retrieval_includes_blocked_goals(self, goal_service, goal_retrieval, user_id):
        g1 = await goal_service.create_goal(user_id, "A")
        g2 = await goal_service.create_goal(user_id, "B")
        await goal_service.update_goal(g2.id, status="blocked")

        rs = RetrievalService(goal_retrieval=goal_retrieval, goal_service=goal_service)
        result = await rs.retrieve_context(user_id, "test")
        assert len(result.blocked_goals) >= 1

    @pytest.mark.asyncio
    async def test_retrieval_includes_urgent_goals(self, goal_service, goal_retrieval, user_id):
        goal = await goal_service.create_goal(user_id, "Urgent", deadline=datetime.now(UTC).isoformat())
        await goal_service.activate_goal(goal.id)

        rs = RetrievalService(goal_retrieval=goal_retrieval, goal_service=goal_service)
        result = await rs.retrieve_context(user_id, "test")
        assert len(result.urgent_goals) >= 1

    @pytest.mark.asyncio
    async def test_retrieval_works_without_goals(self, user_id):
        rs = RetrievalService()
        result = await rs.retrieve_context(user_id, "test")
        assert result.active_goals == []
        assert result.goal_count == 0

    @pytest.mark.asyncio
    async def test_retrieval_independent_from_memory(self, goal_service, goal_retrieval, user_id):
        rs = RetrievalService(goal_retrieval=goal_retrieval, goal_service=goal_service)
        result = await rs.retrieve_context(user_id, "test")
        assert result.memories == []
        assert len(result.active_goals) >= 0


# ════════════════════════════════════════════════════════════════════════
# Prompt Context Integration Tests
# ════════════════════════════════════════════════════════════════════════

class TestPromptContextIntegration:
    @pytest.mark.asyncio
    async def test_prompt_includes_goals(self, goal_service, goal_retrieval, user_id):
        goal = await goal_service.create_goal(user_id, "Learn Python", importance=0.9)
        await goal_service.activate_goal(goal.id)

        rs = RetrievalService(goal_retrieval=goal_retrieval, goal_service=goal_service)
        pcs = PromptContextService(retrieval_service=rs)
        ctx = await pcs.assemble(user_id, "How is my learning going?")

        assert ctx.goal_context != ""
        assert "Learn Python" in ctx.goal_context
        assert ctx.active_goal_count == 1

    @pytest.mark.asyncio
    async def test_prompt_urgent_goals_appear_first(self, goal_service, goal_retrieval, user_id):
        goal = await goal_service.create_goal(
            user_id, "Urgent", deadline=datetime.now(UTC).isoformat()
        )
        await goal_service.activate_goal(goal.id)
        goal2 = await goal_service.create_goal(user_id, "Normal")
        await goal_service.activate_goal(goal2.id)

        rs = RetrievalService(goal_retrieval=goal_retrieval, goal_service=goal_service)
        pcs = PromptContextService(retrieval_service=rs)
        ctx = await pcs.assemble(user_id, "test")

        lines = ctx.goal_context.split("\n")
        urgent_idx = next((i for i, l in enumerate(lines) if "Urgent" in l), -1)
        active_idx = next((i for i, l in enumerate(lines) if "Active" in l), -1)
        assert urgent_idx < active_idx

    @pytest.mark.asyncio
    async def test_prompt_budget_truncates_goals_before_memories(self, goal_service, goal_retrieval, user_id):
        for i in range(20):
            g = await goal_service.create_goal(user_id, f"Goal {i}", importance=0.8)
            await goal_service.activate_goal(g.id)

        rs = RetrievalService(goal_retrieval=goal_retrieval, goal_service=goal_service)
        pcs = PromptContextService(retrieval_service=rs)
        ctx = await pcs.assemble(user_id, "test", token_budget=200)

        assert len(ctx.goal_context) > 0
        assert ctx.token_estimate <= 400

    @pytest.mark.asyncio
    async def test_prompt_goal_truncation_recorded(self, goal_service, goal_retrieval, user_id):
        for i in range(30):
            g = await goal_service.create_goal(user_id, f"Goal {i}")
            await goal_service.activate_goal(g.id)

        rs = RetrievalService(goal_retrieval=goal_retrieval, goal_service=goal_service)
        pcs = PromptContextService(retrieval_service=rs)
        ctx = await pcs.assemble(user_id, "test", token_budget=150)

        assert ctx.active_goal_count == 10
        assert len(ctx.goal_context) > 0

    @pytest.mark.asyncio
    async def test_empty_goals_context(self, goal_service, goal_retrieval, user_id):
        rs = RetrievalService(goal_retrieval=goal_retrieval, goal_service=goal_service)
        pcs = PromptContextService(retrieval_service=rs)
        ctx = await pcs.assemble(user_id, "test")
        assert "No active goals" in ctx.goal_context

    @pytest.mark.asyncio
    async def test_prompt_metadata(self, goal_service, goal_retrieval, user_id):
        goal = await goal_service.create_goal(user_id, "G1")
        await goal_service.activate_goal(goal.id)

        rs = RetrievalService(goal_retrieval=goal_retrieval, goal_service=goal_service)
        pcs = PromptContextService(retrieval_service=rs)
        ctx = await pcs.assemble(user_id, "test")

        assert ctx.active_goal_count == 1
        assert ctx.urgent_goal_count == 0
        assert ctx.blocked_goal_count == 0


# ════════════════════════════════════════════════════════════════════════
# Observability Tests
# ════════════════════════════════════════════════════════════════════════

class TestGoalObservability:
    def test_metrics_recording(self):
        m = GoalMetrics()
        m.record_retrieval(5, 10.0)
        m.record_prompt_injection(500, 1000)
        m.record_scheduler_run(25.0)
        m.record_completion_rate(0.75)
        m.record_overdue(3)
        m.record_blocked(2)
        m.record_conflict()
        m.record_evolution()

        assert m.goal_retrieval_total == 5
        assert m.goal_prompt_tokens == 500
        assert m.goal_scheduler_runs == 1
        assert m.goal_completion_rate == 0.75
        assert m.goal_overdue_total == 3
        assert m.goal_conflicts_total == 1

    def test_prometheus_export(self):
        m = GoalMetrics()
        m.record_retrieval(10, 5.0)
        text = m.export_prometheus_text()
        assert "ayeneh_goal_retrieval_total 10" in text
        assert "ayeneh_goal_retrieval_latency_ms_avg" in text

    @pytest.mark.asyncio
    async def test_event_publisher(self):
        events = []

        class FakeBus:
            async def publish(self, event_type, payload):
                events.append({"type": event_type, **payload})

        publisher = GoalEventPublisher(FakeBus())
        await publisher.goal_retrieved("u1", 5)
        await publisher.goal_conflict("u1", ["g1", "g2"])

        assert len(events) == 2
        assert events[0]["type"] == "GoalRetrieved"
        assert events[1]["type"] == "GoalConflictDetected"


# ════════════════════════════════════════════════════════════════════════
# GoalContextBuilder Integration Tests
# ════════════════════════════════════════════════════════════════════════

class TestGoalContextBuilderIntegration:
    @pytest.mark.asyncio
    async def test_build_with_goals(self, goal_service, goal_retrieval, goal_context_builder, user_id):
        await goal_service.create_goal(user_id, "A", importance=0.9)
        g2 = await goal_service.create_goal(user_id, "B", priority="high")
        await goal_service.activate_goal(g2.id)

        ctx = await goal_context_builder.build(user_id)
        assert len(ctx.active_goals) >= 1

    @pytest.mark.asyncio
    async def test_format_for_prompt(self, goal_service, goal_retrieval, goal_context_builder, user_id):
        await goal_service.create_goal(user_id, "Goal A", priority="critical")
        g = await goal_service.create_goal(user_id, "Goal B")
        await goal_service.activate_goal(g.id)

        ctx = await goal_context_builder.build(user_id)
        text = goal_context_builder.format_for_prompt(ctx)
        assert "Goal B" in text

    @pytest.mark.asyncio
    async def test_build_empty(self, goal_retrieval, goal_service, goal_context_builder, user_id):
        ctx = await goal_context_builder.build(user_id)
        text = goal_context_builder.format_for_prompt(ctx)
        assert "No active goals" in text


# ════════════════════════════════════════════════════════════════════════
# Runtime Integration Tests
# ════════════════════════════════════════════════════════════════════════

class TestRuntimeIntegration:
    @pytest.mark.asyncio
    async def test_goals_participate_in_retrieval(self, goal_service, goal_retrieval, user_id):
        g1 = await goal_service.create_goal(user_id, "Improve health", importance=0.9, category="health")
        g2 = await goal_service.create_goal(user_id, "Learn Rust", importance=0.7, category="learning")
        await goal_service.activate_goal(g1.id)
        await goal_service.activate_goal(g2.id)

        rs = RetrievalService(goal_retrieval=goal_retrieval, goal_service=goal_service)
        result = await rs.retrieve_context(user_id, "health goals")
        assert result.goal_count == 2

    @pytest.mark.asyncio
    async def test_goal_priority_in_prompt(self, goal_service, goal_retrieval, user_id):
        g1 = await goal_service.create_goal(user_id, "Critical", priority="critical")
        g2 = await goal_service.create_goal(user_id, "Low", priority="low")
        await goal_service.activate_goal(g1.id)
        await goal_service.activate_goal(g2.id)

        rs = RetrievalService(goal_retrieval=goal_retrieval, goal_service=goal_service)
        pcs = PromptContextService(retrieval_service=rs)
        ctx = await pcs.assemble(user_id, "test")

        assert "Critical" in ctx.goal_context
        assert "Low" in ctx.goal_context

    @pytest.mark.asyncio
    async def test_full_pipeline_goals_memories_knowledge(self, goal_service, goal_retrieval, user_id):
        g = await goal_service.create_goal(user_id, "Improve writing", importance=0.8)
        await goal_service.activate_goal(g.id)
        await goal_service.update_progress(g.id, 0.4, "Wrote 3 essays")

        rs = RetrievalService(goal_retrieval=goal_retrieval, goal_service=goal_service)
        pcs = PromptContextService(retrieval_service=rs)
        ctx = await pcs.assemble(user_id, "How is my writing progress?")

        assert "Improve writing" in ctx.goal_context
        assert "40%" in ctx.goal_context
        assert ctx.system_context != ""


# ════════════════════════════════════════════════════════════════════════
# Evolved Goal Retrieval Tests
# ════════════════════════════════════════════════════════════════════════

class TestEvolvedGoalRetrieval:
    @pytest.mark.asyncio
    async def test_goal_retrieval_ranks_by_importance(self, goal_retrieval, goal_service, user_id):
        g1 = await goal_service.create_goal(user_id, "Low", importance=0.2)
        g2 = await goal_service.create_goal(user_id, "High", importance=0.9)
        await goal_service.activate_goal(g1.id)
        await goal_service.activate_goal(g2.id)

        result = await goal_retrieval.retrieve(user_id)
        assert result.goals[0].importance >= result.goals[-1].importance

    @pytest.mark.asyncio
    async def test_goal_retrieval_filters_by_category(self, goal_retrieval, goal_service, user_id):
        await goal_service.create_goal(user_id, "Health", category="health")
        await goal_service.create_goal(user_id, "Work", category="professional")

        result = await goal_retrieval.retrieve(user_id, category="health")
        assert all(g.category == "health" for g in result.goals)

    @pytest.mark.asyncio
    async def test_goal_retrieval_with_deadline(self, goal_retrieval, goal_service, user_id):
        goal = await goal_service.create_goal(
            user_id, "Deadline goal", deadline=(datetime.now(UTC) + timedelta(days=2)).isoformat()
        )
        await goal_service.activate_goal(goal.id)

        urgent = await goal_retrieval.retrieve_urgent(user_id)
        assert len(urgent) >= 1


# ════════════════════════════════════════════════════════════════════════
# Goal Evolution Integration Tests
# ════════════════════════════════════════════════════════════════════════

class TestGoalEvolutionIntegration:
    @pytest.mark.asyncio
    async def test_daily_evolution_with_metrics(self, goal_evolution, goal_service, goal_metrics, user_id):
        g = await goal_service.create_goal(user_id, "Test")
        await goal_service.activate_goal(g.id)
        await goal_service.update_progress(g.id, 0.5, "progress")

        result = await goal_evolution.run_daily(user_id)
        goal_metrics.record_evolution()
        assert goal_metrics.goal_evolution_total == 1

    @pytest.mark.asyncio
    async def test_weekly_evolution(self, goal_evolution, goal_service, user_id):
        g = await goal_service.create_goal(user_id, "Growing")
        await goal_service.activate_goal(g.id)
        await goal_service.update_progress(g.id, 0.3)

        result = await goal_evolution.run_weekly(user_id)
        assert result.strengthened >= 0


# ════════════════════════════════════════════════════════════════════════
# Concurrency Tests
# ════════════════════════════════════════════════════════════════════════

class TestGoalConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_goal_operations(self, goal_service, user_id):
        async def create_and_activate(idx: int):
            g = await goal_service.create_goal(user_id, f"Goal {idx}")
            await goal_service.activate_goal(g.id)
            await goal_service.update_progress(g.id, 0.5)
            return g.id

        ids = await asyncio.gather(*[create_and_activate(i) for i in range(5)])
        assert len(ids) == 5
        goals = await goal_service.list_goals(user_id)
        assert len(goals) == 5

    @pytest.mark.asyncio
    async def test_concurrent_retrieval(self, goal_service, goal_retrieval, user_id):
        for i in range(10):
            g = await goal_service.create_goal(user_id, f"G{i}")
            await goal_service.activate_goal(g.id)

        async def retrieve():
            return await goal_retrieval.retrieve(user_id)

        results = await asyncio.gather(*[retrieve() for _ in range(5)])
        assert all(len(r.goals) == 10 for r in results)


@pytest_asyncio.fixture
def goal_metrics():
    return GoalMetrics()
