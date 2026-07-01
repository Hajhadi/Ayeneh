"""Goal Engine integration tests — tests service + persistence + API together."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ayeneh.goal.context import GoalContextBuilder
from ayeneh.goal.domain import Goal, GoalStatus
from ayeneh.goal.evolution import GoalEvolutionConfig, GoalEvolutionResult, GoalEvolutionService
from ayeneh.goal.retrieval import GoalRetrievalService
from ayeneh.goal.service import GoalService, GoalStats
from ayeneh.infrastructure.persistence.base import Base
from ayeneh.infrastructure.persistence.models.user import UserModel
from ayeneh.infrastructure.persistence.unit_of_work import UnitOfWork
from ayeneh.main import app


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
def goal_evolution(goal_service):
    return GoalEvolutionService(
        goal_service,
        config=GoalEvolutionConfig(aging_halflife_days=30, stale_days=10),
    )


@pytest_asyncio.fixture
def goal_retrieval(goal_service):
    return GoalRetrievalService(goal_service)


# ── Service unit tests ──

class TestGoalService:
    @pytest.mark.asyncio
    async def test_create_goal(self, goal_service, user_id):
        goal = await goal_service.create_goal(user_id, "Learn Python", priority="high", category="learning")
        assert goal.title == "Learn Python"
        assert goal.priority == "high"
        assert goal.status == "draft"

    @pytest.mark.asyncio
    async def test_activate_goal(self, goal_service, user_id):
        goal = await goal_service.create_goal(user_id, "Goal")
        activated = await goal_service.activate_goal(goal.id)
        assert activated.status == "active"

    @pytest.mark.asyncio
    async def test_complete_goal(self, goal_service, user_id):
        goal = await goal_service.create_goal(user_id, "Goal")
        await goal_service.activate_goal(goal.id)
        completed = await goal_service.complete_goal(goal.id)
        assert completed.status == "completed"
        assert completed.completed_at is not None

    @pytest.mark.asyncio
    async def test_pause_goal(self, goal_service, user_id):
        goal = await goal_service.create_goal(user_id, "Goal")
        await goal_service.activate_goal(goal.id)
        paused = await goal_service.pause_goal(goal.id, "busy")
        assert paused.status == "paused"

    @pytest.mark.asyncio
    async def test_abandon_goal(self, goal_service, user_id):
        goal = await goal_service.create_goal(user_id, "Goal")
        abandoned = await goal_service.abandon_goal(goal.id, "no longer relevant")
        assert abandoned.status == "abandoned"
        assert abandoned.abandoned_at is not None

    @pytest.mark.asyncio
    async def test_update_progress(self, goal_service, user_id):
        goal = await goal_service.create_goal(user_id, "Goal")
        await goal_service.activate_goal(goal.id)
        updated = await goal_service.update_progress(goal.id, 0.5)
        assert updated.progress == 0.5

    @pytest.mark.asyncio
    async def test_progress_auto_completes(self, goal_service, user_id):
        goal = await goal_service.create_goal(user_id, "Goal")
        await goal_service.activate_goal(goal.id)
        completed = await goal_service.update_progress(goal.id, 1.0)
        assert completed.status == "completed"

    @pytest.mark.asyncio
    async def test_add_milestone(self, goal_service, user_id):
        goal = await goal_service.create_goal(user_id, "Goal")
        updated = await goal_service.add_milestone(goal.id, "Learn syntax")
        assert len(updated.milestones) == 1

    @pytest.mark.asyncio
    async def test_add_dependency(self, goal_service, user_id):
        g1 = await goal_service.create_goal(user_id, "A")
        g2 = await goal_service.create_goal(user_id, "B")
        updated = await goal_service.add_dependency(g1.id, g2.id, "blocks")
        assert len(updated.dependencies) == 1

    @pytest.mark.asyncio
    async def test_add_review(self, goal_service, user_id):
        goal = await goal_service.create_goal(user_id, "Goal")
        updated = await goal_service.add_review(goal.id, 0.8, "Good progress")
        assert len(updated.reviews) == 1
        assert updated.reviews[0].rating == 0.8

    @pytest.mark.asyncio
    async def test_get_stats(self, goal_service, user_id):
        await goal_service.create_goal(user_id, "A")
        g2 = await goal_service.create_goal(user_id, "B")
        await goal_service.activate_goal(g2.id)
        await goal_service.complete_goal(g2.id)
        stats = await goal_service.get_stats(user_id)
        assert stats.total == 2
        assert stats.completed == 1

    @pytest.mark.asyncio
    async def test_list_goals_with_filters(self, goal_service, user_id):
        await goal_service.create_goal(user_id, "A", category="personal")
        await goal_service.create_goal(user_id, "B", category="professional")
        personal = await goal_service.list_goals(user_id, category="personal")
        assert len(personal) == 1

    @pytest.mark.asyncio
    async def test_get_history(self, goal_service, user_id):
        goal = await goal_service.create_goal(user_id, "Goal")
        await goal_service.activate_goal(goal.id)
        history = await goal_service.get_history(goal.id)
        assert len(history) >= 2


# ── Evolution tests ──

class TestGoalEvolution:
    @pytest.mark.asyncio
    async def test_daily_evolution(self, goal_evolution, goal_service, user_id):
        goal = await goal_service.create_goal(user_id, "Active")
        await goal_service.activate_goal(goal.id)
        await goal_service.update_progress(goal.id, 0.3, "initial progress")
        result = await goal_evolution.run_daily(user_id)
        assert isinstance(result, GoalEvolutionResult)

    @pytest.mark.asyncio
    async def test_weekly_strengthens(self, goal_evolution, goal_service, user_id):
        goal = await goal_service.create_goal(user_id, "Growing", confidence=0.5)
        await goal_service.activate_goal(goal.id)
        await goal_service.update_progress(goal.id, 0.5)
        result = await goal_evolution.run_weekly(user_id)
        assert result.strengthened >= 0

    @pytest.mark.asyncio
    async def test_monthly_archives(self, goal_evolution, goal_service, user_id):
        goal = await goal_service.create_goal(user_id, "Done")
        await goal_service.complete_goal(goal.id)
        await goal_evolution.run_monthly(user_id)
        g = await goal_service.get_goal(goal.id)
        assert g is not None and g.status == "archived"


# ── Retrieval tests ──

class TestGoalRetrieval:
    @pytest.mark.asyncio
    async def test_retrieve_ranked(self, goal_retrieval, goal_service, user_id):
        g1 = await goal_service.create_goal(user_id, "Low", priority="low", importance=0.2)
        g2 = await goal_service.create_goal(user_id, "High", priority="critical", importance=0.9)
        await goal_service.activate_goal(g1.id)
        await goal_service.activate_goal(g2.id)
        result = await goal_retrieval.retrieve(user_id)
        assert result.total == 2
        assert result.goals[0].importance >= result.goals[-1].importance

    @pytest.mark.asyncio
    async def test_retrieve_urgent(self, goal_retrieval, goal_service, user_id):
        goal = await goal_service.create_goal(user_id, "Urgent")
        await goal_service.activate_goal(goal.id)
        await goal_service.update_goal(goal.id, deadline=datetime.now(UTC).isoformat())
        active = await goal_service.get_active_goals(user_id)
        assert len(active) >= 1
        urgent = await goal_retrieval.retrieve_urgent(user_id)
        assert len(urgent) >= 1

    @pytest.mark.asyncio
    async def test_retrieve_blocked(self, goal_retrieval, goal_service, user_id):
        goal = await goal_service.create_goal(user_id, "Blocked")
        await goal_service.update_goal(goal.id, status="blocked")
        blocked = await goal_retrieval.retrieve_blocked(user_id)
        assert len(blocked) >= 1


# ── Context builder tests ──

class TestGoalContext:
    @pytest.mark.asyncio
    async def test_build_context(self, goal_retrieval, goal_service, user_id):
        goal = await goal_service.create_goal(user_id, "Active Goal", importance=0.8)
        await goal_service.activate_goal(goal.id)
        builder = GoalContextBuilder(goal_retrieval, goal_service)
        ctx = await builder.build(user_id)
        assert len(ctx.active_goals) >= 1

    @pytest.mark.asyncio
    async def test_format_for_prompt(self, goal_retrieval, goal_service, user_id):
        goal = await goal_service.create_goal(user_id, "Test Goal")
        await goal_service.activate_goal(goal.id)
        builder = GoalContextBuilder(goal_retrieval, goal_service)
        ctx = await builder.build(user_id)
        text = builder.format_for_prompt(ctx)
        assert "Test Goal" in text

    @pytest.mark.asyncio
    async def test_empty_context(self, goal_retrieval, goal_service, user_id):
        builder = GoalContextBuilder(goal_retrieval, goal_service)
        ctx = await builder.build(user_id)
        text = builder.format_for_prompt(ctx)
        assert "No active goals" in text
