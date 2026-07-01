"""Tests for runtime planner and executor."""

from __future__ import annotations

import pytest

from ayeneh.agents.conversation import ConversationAgent
from ayeneh.agents.memory import MemoryAgent
from ayeneh.infrastructure.repositories.event_bus import InMemoryEventBus
from ayeneh.runtime.context import ExecutionContext
from ayeneh.runtime.executor import ExecutionExecutor
from ayeneh.runtime.planner import (
    ExecutionPlan,
    ExecutionPlanner,
    LLMPlanner,
    PlanStep,
    PlanTemplate,
    RulePlanner,
)


@pytest.fixture
def agents() -> dict:
    return {
        "conversation": ConversationAgent(),
        "memory": MemoryAgent(),
    }


@pytest.fixture
def event_bus() -> InMemoryEventBus:
    return InMemoryEventBus()


@pytest.mark.asyncio
async def test_planner_returns_plan() -> None:
    rule = RulePlanner(templates=[PlanTemplate("g", ["hello"], [PlanStep(step_id="s1", agent_name="conversation")])])
    planner = ExecutionPlanner(rule, LLMPlanner(), confidence_threshold=0.3)
    plan = await planner.plan("hello there")
    assert len(plan.steps) > 0
    assert plan.strategy == "rule_based"


@pytest.mark.asyncio
async def test_executor_runs_plan(agents: dict) -> None:
    executor = ExecutionExecutor(agents=agents)
    plan = ExecutionPlan(
        steps=[
            PlanStep(step_id="s1", agent_name="conversation"),
            PlanStep(step_id="s2", agent_name="memory"),
        ]
    )
    ctx = ExecutionContext(user_id="u1")
    result = await executor.execute(plan, ctx)
    assert "step_results" in result
    assert "s1" in result["step_results"]
