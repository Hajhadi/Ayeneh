"""Tests for Goal-Aware Reasoning integration across all cognitive agents."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ayeneh.application.services.prompt_context import PromptContextService
from ayeneh.application.services.retrieval import RetrievalResult, RetrievalService
from ayeneh.evaluation.core import EvalCase
from ayeneh.goal.context import GoalContextBuilder
from ayeneh.goal.coordination import GoalCoordinationMessage, GoalCoordinationService, AgentGoalReference
from ayeneh.goal.domain import Goal, GoalStatus
from ayeneh.goal.evaluation import (
    CONVERSATION_GOAL_BENCHMARKS,
    PATTERN_GOAL_BENCHMARKS,
    REFLECTION_GOAL_BENCHMARKS,
    BLIND_SPOT_GOAL_BENCHMARKS,
    get_all_goal_benchmarks,
    get_goal_benchmarks,
)
from ayeneh.goal.grounding.metadata import GoalReasoningMetadata, attach_goal_metadata
from ayeneh.goal.grounding.prompt_builder import GoalPromptBuilder, GoalPromptSelection
from ayeneh.goal.grounding.service import GoalGroundingResult, GoalGroundingService, GroundedGoal
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
def goal_grounding(goal_service, goal_retrieval):
    return GoalGroundingService(goal_service, goal_retrieval)


@pytest_asyncio.fixture
def goal_prompt_builder(goal_grounding):
    return GoalPromptBuilder(goal_grounding)


@pytest_asyncio.fixture
def coordination():
    return GoalCoordinationService()


async def _setup_goals(goal_service, user_id: str) -> list[Goal]:
    g1 = await goal_service.create_goal(user_id, "Learn Python", priority="high", importance=0.9)
    await goal_service.activate_goal(g1.id)
    g2 = await goal_service.create_goal(user_id, "Exercise daily", priority="medium", importance=0.6)
    await goal_service.activate_goal(g2.id)
    await goal_service.update_progress(g2.id, 0.5)
    g3 = await goal_service.create_goal(user_id, "Read 12 books", priority="critical",
                                        deadline=(datetime.now(UTC) + timedelta(days=30)).isoformat())
    await goal_service.activate_goal(g3.id)
    return [g1, g2, g3]


# ════════════════════════════════════════════════════════════════════════
# Goal Grounding Tests
# ════════════════════════════════════════════════════════════════════════

class TestGoalGrounding:
    @pytest.mark.asyncio
    async def test_ground_goals(self, goal_grounding, goal_service, user_id):
        goals = await _setup_goals(goal_service, user_id)
        result = await goal_grounding.ground_goals(user_id)
        assert result.total_goals_evaluated == 3
        assert result.goals_selected >= 1
        assert all(g.goal_id for g in result.grounded_goals)

    @pytest.mark.asyncio
    async def test_ground_specific_goals(self, goal_grounding, goal_service, user_id):
        goals = await _setup_goals(goal_service, user_id)
        result = await goal_grounding.ground_goals(user_id, candidate_goal_ids=[goals[0].id])
        assert result.goals_selected == 1
        assert result.grounded_goals[0].title == "Learn Python"

    @pytest.mark.asyncio
    async def test_ground_rejects_unknown_goals(self, goal_grounding, goal_service, user_id):
        await _setup_goals(goal_service, user_id)
        result = await goal_grounding.ground_goals(
            user_id, candidate_goal_ids=["nonexistent-id"]
        )
        assert result.goals_rejected == 1
        assert result.goals_selected == 0

    @pytest.mark.asyncio
    async def test_validate_grounding_passes(self, goal_grounding, goal_service, user_id):
        goals = await _setup_goals(goal_service, user_id)
        result = await goal_grounding.ground_goals(user_id)
        agent_output = {"referenced_goal_ids": [goals[0].id]}
        valid, issues = goal_grounding.validate_grounding(agent_output, result)
        assert valid is True
        assert issues == []

    @pytest.mark.asyncio
    async def test_validate_grounding_fails(self, goal_grounding, goal_service, user_id):
        goals = await _setup_goals(goal_service, user_id)
        result = await goal_grounding.ground_goals(user_id)
        agent_output = {"referenced_goal_ids": ["fake-id"]}
        valid, issues = goal_grounding.validate_grounding(agent_output, result)
        assert valid is False
        assert len(issues) == 1

    @pytest.mark.asyncio
    async def test_grounding_includes_metadata(self, goal_grounding, goal_service, user_id):
        await _setup_goals(goal_service, user_id)
        result = await goal_grounding.ground_goals(user_id)
        for g in result.grounded_goals:
            assert g.source == "goal_service"
            assert g.confidence > 0


# ════════════════════════════════════════════════════════════════════════
# Goal Prompt Builder Tests
# ════════════════════════════════════════════════════════════════════════

class TestGoalPromptBuilder:
    @pytest.mark.asyncio
    async def test_build_for_conversation(self, goal_prompt_builder, goal_service, user_id):
        await _setup_goals(goal_service, user_id)
        selection = await goal_prompt_builder.build_goal_prompt(
            user_id, {"query": "How is my learning going?"}, agent_type="conversation"
        )
        assert selection.selected_count >= 1
        assert len(selection.goals) >= 1
        text = goal_prompt_builder.format_goals_for_agent(selection, "conversation")
        assert "Learn Python" in text

    @pytest.mark.asyncio
    async def test_build_for_reflection(self, goal_prompt_builder, goal_service, user_id):
        await _setup_goals(goal_service, user_id)
        selection = await goal_prompt_builder.build_goal_prompt(
            user_id, {"query": "reflect on my goals"}, agent_type="reflection"
        )
        text = goal_prompt_builder.format_goals_for_agent(selection, "reflection")
        assert "Goals to reflect upon" in text

    @pytest.mark.asyncio
    async def test_build_for_blind_spot(self, goal_prompt_builder, goal_service, user_id):
        await _setup_goals(goal_service, user_id)
        selection = await goal_prompt_builder.build_goal_prompt(
            user_id, {"query": "check my blind spots"}, agent_type="blind_spot"
        )
        text = goal_prompt_builder.format_goals_for_agent(selection, "blind_spot")
        assert "blind spots" in text.lower()

    @pytest.mark.asyncio
    async def test_build_for_pattern(self, goal_prompt_builder, goal_service, user_id):
        await _setup_goals(goal_service, user_id)
        selection = await goal_prompt_builder.build_goal_prompt(
            user_id, {"query": "detect patterns"}, agent_type="pattern"
        )
        text = goal_prompt_builder.format_goals_for_agent(selection, "pattern")
        assert "pattern analysis" in text.lower()

    @pytest.mark.asyncio
    async def test_budget_truncation(self, goal_prompt_builder, goal_service, user_id):
        await _setup_goals(goal_service, user_id)
        selection = await goal_prompt_builder.build_goal_prompt(
            user_id, {"query": "test"}, token_budget=50
        )
        assert selection.token_estimate <= 200

    @pytest.mark.asyncio
    async def test_relevance_scoring(self, goal_prompt_builder, goal_service, user_id):
        goals = await _setup_goals(goal_service, user_id)
        selection = await goal_prompt_builder.build_goal_prompt(
            user_id, {"query": "Python learning progress"}, agent_type="conversation"
        )
        python_goal = [g for g in selection.goals if "Python" in g.title]
        assert len(python_goal) >= 1

    @pytest.mark.asyncio
    async def test_empty_goals(self, goal_prompt_builder, user_id):
        selection = await goal_prompt_builder.build_goal_prompt(
            user_id, {"query": "test"}, agent_type="conversation"
        )
        text = goal_prompt_builder.format_goals_for_agent(selection, "conversation")
        assert text == ""


# ════════════════════════════════════════════════════════════════════════
# Cross-Agent Coordination Tests
# ════════════════════════════════════════════════════════════════════════

class TestGoalCoordination:
    def test_register_and_retrieve(self, coordination):
        refs = [
            AgentGoalReference(
                agent_name="pattern", goal_id="g1", goal_title="Goal A",
                reference_type="observation", reasoning="Detected avoidance",
            )
        ]
        coordination.register_references("pattern", refs)
        result = coordination.get_references_from("pattern")
        assert len(result) == 1
        assert result[0].goal_id == "g1"

    def test_send_and_receive_messages(self, coordination):
        msg = GoalCoordinationMessage(
            source_agent="reflection",
            target_agent="conversation",
            references=[AgentGoalReference(
                agent_name="reflection", goal_id="g1",
                goal_title="Goal A", reference_type="suggestion",
            )],
        )
        coordination.send_message(msg)
        messages = coordination.get_messages_for("conversation")
        assert len(messages) == 1

    def test_clear(self, coordination):
        coordination.register_references("a", [AgentGoalReference(agent_name="a", goal_id="1", goal_title="X")])
        coordination.send_message(GoalCoordinationMessage(source_agent="a", references=[]))
        coordination.clear()
        assert len(coordination.get_references_from("a")) == 0
        assert len(coordination.get_messages_for("a")) == 0

    def test_filtered_retrieval(self, coordination):
        refs = [
            AgentGoalReference(agent_name="a", goal_id="1", goal_title="X", reference_type="observation"),
            AgentGoalReference(agent_name="a", goal_id="2", goal_title="Y", reference_type="internal"),
        ]
        coordination.register_references("a", refs)
        filtered = coordination.get_references_from("a", target_agent="conversation")
        assert len(filtered) == 1


# ════════════════════════════════════════════════════════════════════════
# Grounding Metadata Tests
# ════════════════════════════════════════════════════════════════════════

class TestGroundingMetadata:
    def test_reasoning_metadata(self):
        meta = GoalReasoningMetadata(
            agent_name="conversation",
            goals_used=[{"goal_id": "g1"}],
            reasoning_confidence=0.8,
            explanation="Goal matched user query",
        )
        d = meta.to_dict()
        assert d["agent_name"] == "conversation"
        assert len(d["goals_used"]) == 1

    def test_attach_metadata(self):
        data = {"response_text": "hello"}
        result = attach_goal_metadata(data, "conversation", ["g1"], ["g2"], "matched query")
        assert "goal_reasoning" in result
        assert result["goal_reasoning"]["agent_name"] == "conversation"
        assert len(result["goal_reasoning"]["goals_used"]) == 1
        assert len(result["goal_reasoning"]["goals_ignored"]) == 1


# ════════════════════════════════════════════════════════════════════════
# Evaluation Benchmarks Tests
# ════════════════════════════════════════════════════════════════════════

class TestGoalEvaluation:
    def test_benchmarks_exist(self):
        assert len(CONVERSATION_GOAL_BENCHMARKS) >= 3
        assert len(PATTERN_GOAL_BENCHMARKS) >= 2
        assert len(REFLECTION_GOAL_BENCHMARKS) >= 1
        assert len(BLIND_SPOT_GOAL_BENCHMARKS) >= 1

    def test_get_goal_benchmarks(self):
        conv = get_goal_benchmarks("conversation")
        assert len(conv) >= 3
        for b in conv:
            assert b.agent_type == "conversation"

    def test_get_all_goal_benchmarks(self):
        all_b = get_all_goal_benchmarks()
        assert len(all_b) >= 7
        agent_types = {b.agent_type for b in all_b}
        assert "conversation" in agent_types
        assert "pattern" in agent_types
        assert "reflection" in agent_types
        assert "blind_spot" in agent_types

    def test_benchmarks_have_goal_references(self):
        for b in get_all_goal_benchmarks():
            expected = b.expected_output
            if "referenced_goals" in expected:
                assert isinstance(expected["referenced_goals"], list)


# ════════════════════════════════════════════════════════════════════════
# Integration: Retrieval + Goals
# ════════════════════════════════════════════════════════════════════════

class TestGoalRetrievalIntegration:
    @pytest.mark.asyncio
    async def test_retrieval_returns_goals(self, goal_service, goal_retrieval, user_id):
        await _setup_goals(goal_service, user_id)
        rs = RetrievalService(goal_retrieval=goal_retrieval, goal_service=goal_service)
        result = await rs.retrieve_context(user_id, "learning goals")
        assert result.goal_count >= 1
        assert len(result.active_goals) >= 1

    @pytest.mark.asyncio
    async def test_prompt_context_includes_goals(self, goal_service, goal_retrieval, user_id):
        await _setup_goals(goal_service, user_id)
        rs = RetrievalService(goal_retrieval=goal_retrieval, goal_service=goal_service)
        pcs = PromptContextService(retrieval_service=rs)
        ctx = await pcs.assemble(user_id, "Python progress")
        assert "Learn Python" in ctx.goal_context
        assert ctx.active_goal_count >= 1

    @pytest.mark.asyncio
    async def test_goal_budget_priority(self, goal_service, goal_retrieval, user_id):
        for i in range(20):
            g = await goal_service.create_goal(user_id, f"Goal {i}")
            await goal_service.activate_goal(g.id)
        rs = RetrievalService(goal_retrieval=goal_retrieval, goal_service=goal_service)
        pcs = PromptContextService(retrieval_service=rs)
        ctx = await pcs.assemble(user_id, "test", token_budget=100)
        assert ctx.token_estimate < 300


# ════════════════════════════════════════════════════════════════════════
# Agent Grounding Tests
# ════════════════════════════════════════════════════════════════════════

class TestAgentGrounding:
    @pytest.mark.asyncio
    async def test_conversation_agent_receives_goals(
        self, goal_grounding, goal_service, user_id
    ):
        await _setup_goals(goal_service, user_id)
        grounding = await goal_grounding.ground_goals(user_id)
        goal_ids = [g.goal_id for g in grounding.grounded_goals]
        assert len(goal_ids) >= 1

    @pytest.mark.asyncio
    async def test_pattern_agent_receives_goals(
        self, goal_grounding, goal_service, user_id
    ):
        await _setup_goals(goal_service, user_id)
        grounding = await goal_grounding.ground_goals(user_id, max_goals=5)
        assert grounding.goals_selected <= 5

    @pytest.mark.asyncio
    async def test_blind_spot_uses_goals_for_analysis(
        self, goal_grounding, goal_service, user_id
    ):
        g = await goal_service.create_goal(user_id, "Exercise daily", priority="high")
        await goal_service.activate_goal(g.id)
        await goal_service.update_progress(g.id, 0.0)
        grounding = await goal_grounding.ground_goals(user_id)
        assert any(gl.goal_id == g.id for gl in grounding.grounded_goals)

    @pytest.mark.asyncio
    async def test_reflection_goals_context(
        self, goal_grounding, goal_service, user_id
    ):
        await _setup_goals(goal_service, user_id)
        goal_builder = GoalContextBuilder(GoalRetrievalService(goal_service), goal_service)
        ctx = await goal_builder.build(user_id)
        assert len(ctx.active_goals) >= 1
        text = goal_builder.format_for_prompt(ctx)
        assert len(text) > 0


# ════════════════════════════════════════════════════════════════════════
# Concurrency Tests
# ════════════════════════════════════════════════════════════════════════

class TestGoalConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_grounding(self, goal_grounding, goal_service, user_id):
        await _setup_goals(goal_service, user_id)

        async def ground():
            return await goal_grounding.ground_goals(user_id)

        results = await asyncio.gather(*[ground() for _ in range(5)])
        assert all(r.total_goals_evaluated == 3 for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_prompt_building(self, goal_prompt_builder, goal_service, user_id):
        await _setup_goals(goal_service, user_id)

        async def build(agent_type: str):
            return await goal_prompt_builder.build_goal_prompt(
                user_id, {"query": "test"}, agent_type=agent_type
            )

        results = await asyncio.gather(*[build(t) for t in ["conversation", "reflection", "pattern"]])
        assert all(r.selected_count >= 1 for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_coordination(self, coordination):
        async def register(idx: int):
            refs = [AgentGoalReference(
                agent_name=f"agent_{idx}", goal_id=f"g{idx}",
                goal_title=f"Goal {idx}",
            )]
            coordination.register_references(f"agent_{idx}", refs)

        await asyncio.gather(*[register(i) for i in range(10)])
        assert len(coordination.get_all_references()) == 10


# ════════════════════════════════════════════════════════════════════════
# Failure Recovery Tests
# ════════════════════════════════════════════════════════════════════════

class TestGoalFailureRecovery:
    @pytest.mark.asyncio
    async def test_grounding_handles_missing_goals(self, goal_grounding, user_id):
        result = await goal_grounding.ground_goals(user_id)
        assert result.goals_selected == 0
        assert result.grounding_latency_ms >= 0

    @pytest.mark.asyncio
    async def test_prompt_builder_handles_empty_retrieval(self, goal_prompt_builder, user_id):
        selection = await goal_prompt_builder.build_goal_prompt(
            user_id, {"query": "empty"}, agent_type="conversation"
        )
        assert selection.selected_count == 0
        text = goal_prompt_builder.format_goals_for_agent(selection, "conversation")
        assert text == ""

    @pytest.mark.asyncio
    async def test_coordination_handles_unknown_agent(self, coordination):
        refs = coordination.get_references_from("nonexistent")
        assert refs == []
        messages = coordination.get_messages_for("nonexistent")
        assert messages == []
