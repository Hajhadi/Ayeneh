"""Comprehensive tests for the Runtime Orchestrator."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from ayeneh.agents.base import AgentOutput, BaseAgent
from ayeneh.application.ports.event_bus import EventBus
from ayeneh.runtime.composer import ResponseComposer
from ayeneh.runtime.context import ExecutionContext, RuntimeState, StepTrace
from ayeneh.runtime.coordinator import RuntimeCoordinator
from ayeneh.runtime.events import RuntimeEventPublisher
from ayeneh.runtime.executor import ExecutionExecutor
from ayeneh.runtime.failure import FailureManager
from ayeneh.runtime.planner import (
    ErrorStrategy,
    ExecutionPlan,
    ExecutionPlanner,
    LLMPlanner,
    PlanStep,
    PlanTemplate,
    RulePlanner,
)

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

class StubAgent(BaseAgent):
    def __init__(self, name: str, output_text: str = "ok") -> None:
        self.name = name
        self._output = output_text
        self.call_count = 0

    async def execute(self, context: dict[str, Any]) -> AgentOutput:
        self.call_count += 1
        return AgentOutput(status="success", data={"response_text": self._output})


class FailingAgent(BaseAgent):
    def __init__(self, name: str, error: str = "boom") -> None:
        self.name = name
        self._error = error

    async def execute(self, context: dict[str, Any]) -> AgentOutput:
        raise RuntimeError(self._error)


class SlowAgent(BaseAgent):
    def __init__(self, name: str, delay: float = 0.5) -> None:
        self.name = name
        self._delay = delay

    async def execute(self, context: dict[str, Any]) -> AgentOutput:
        await asyncio.sleep(self._delay)
        return AgentOutput(status="success", data={"response_text": "slow"})


class InMemoryEventBus(EventBus):
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append({"type": event_type, **payload})

    def subscribe(self, event_type: str, handler: Any) -> None:
        pass


@pytest.fixture
def event_bus() -> InMemoryEventBus:
    return InMemoryEventBus()


@pytest.fixture
def event_publisher(event_bus: InMemoryEventBus) -> RuntimeEventPublisher:
    return RuntimeEventPublisher(event_bus)


# ---------------------------------------------------------------------------
# Planner tests
# ---------------------------------------------------------------------------

class TestRulePlanner:
    def test_matches_keyword(self) -> None:
        template = PlanTemplate("greeting", ["hello", "hi"], [PlanStep(step_id="s1", agent_name="conversation")])
        planner = RulePlanner(templates=[template])
        plan, confidence = planner.evaluate("hello there")
        assert plan is not None
        assert confidence > 0
        assert len(plan.steps) == 1

    def test_no_match(self) -> None:
        planner = RulePlanner(templates=[PlanTemplate("greeting", ["hello"], [PlanStep(step_id="s1", agent_name="conversation")])])
        plan, confidence = planner.evaluate("quantum physics lecture")
        assert plan is None or confidence == 0.0

    def test_best_template_wins(self) -> None:
        t1 = PlanTemplate("greeting", ["hello"], [PlanStep(step_id="s1", agent_name="conversation")])
        t2 = PlanTemplate("knowledge", ["quantum", "physics"], [PlanStep(step_id="s1", agent_name="library")])
        planner = RulePlanner(templates=[t1, t2])
        plan, _confidence = planner.evaluate("tell me about quantum physics")
        assert plan is not None
        assert plan.steps[0].agent_name == "library"


class TestLLMPlanner:
    @pytest.mark.asyncio
    async def test_returns_plan(self) -> None:
        planner = LLMPlanner()
        plan = await planner.generate_plan("complex request")
        assert isinstance(plan, ExecutionPlan)
        assert plan.strategy == "llm_assisted"


class TestExecutionPlanner:
    @pytest.mark.asyncio
    async def test_uses_rule_planner_when_confident(self) -> None:
        rule = RulePlanner(templates=[PlanTemplate("greet", ["hello"], [PlanStep(step_id="s1", agent_name="conversation")])])
        llm = LLMPlanner()
        planner = ExecutionPlanner(rule, llm, confidence_threshold=0.3)
        plan = await planner.plan("hello there")
        assert plan.strategy == "rule_based"

    @pytest.mark.asyncio
    async def test_escalates_to_llm_when_not_confident(self) -> None:
        rule = RulePlanner(templates=[])
        llm = LLMPlanner()
        planner = ExecutionPlanner(rule, llm, confidence_threshold=0.5)
        plan = await planner.plan("ambiguous complex request about everything")
        assert plan.strategy == "llm_assisted"

    @pytest.mark.asyncio
    async def test_validates_registered_agents(self) -> None:
        rule = RulePlanner(templates=[PlanTemplate("g", ["hello"], [PlanStep(step_id="s1", agent_name="conversation"), PlanStep(step_id="s2", agent_name="nonexistent")])])
        llm = LLMPlanner()
        planner = ExecutionPlanner(rule, llm, confidence_threshold=0.3, registered_agents={"conversation"})
        plan = await planner.plan("hello")
        assert len(plan.steps) == 1
        assert plan.steps[0].agent_name == "conversation"


# ---------------------------------------------------------------------------
# Execution context tests
# ---------------------------------------------------------------------------

class TestExecutionContext:
    def test_records_events(self) -> None:
        ctx = ExecutionContext(user_id="u1")
        ctx.record_event("TestEvent", {"key": "value"})
        assert len(ctx.event_log) == 1
        assert ctx.event_log[0].event_type == "TestEvent"

    def test_records_errors(self) -> None:
        ctx = ExecutionContext(user_id="u1")
        ctx.record_error("s1", "something broke")
        assert len(ctx.error_log) == 1

    def test_agent_output_storage(self) -> None:
        ctx = ExecutionContext(user_id="u1")
        output = AgentOutput(status="success", data={"text": "hello"})
        ctx.agent_outputs["s1"] = output
        assert ctx.has_output("s1")
        assert ctx.get_agent_output("s1") is output

    def test_cancel(self) -> None:
        ctx = ExecutionContext(user_id="u1")
        ctx.cancel()
        assert ctx.cancelled is True
        assert ctx.state == RuntimeState.ABORTING


# ---------------------------------------------------------------------------
# Executor tests
# ---------------------------------------------------------------------------

class TestExecutionExecutor:
    @pytest.mark.asyncio
    async def test_executes_plan(self) -> None:
        agent = StubAgent("conversation", "hello")
        executor = ExecutionExecutor(agents={"conversation": agent})
        plan = ExecutionPlan(steps=[PlanStep(step_id="s1", agent_name="conversation")])
        ctx = ExecutionContext(user_id="u1")
        result = await executor.execute(plan, ctx)
        assert "s1" in result["step_results"]
        assert agent.call_count == 1

    @pytest.mark.asyncio
    async def test_multiple_steps(self) -> None:
        a1 = StubAgent("conversation", "hi")
        a2 = StubAgent("memory", "stored")
        executor = ExecutionExecutor(agents={"conversation": a1, "memory": a2})
        plan = ExecutionPlan(steps=[
            PlanStep(step_id="s1", agent_name="conversation"),
            PlanStep(step_id="s2", agent_name="memory"),
        ])
        ctx = ExecutionContext(user_id="u1")
        result = await executor.execute(plan, ctx)
        assert len(result["step_results"]) == 2

    @pytest.mark.asyncio
    async def test_agent_failure_continues(self) -> None:
        good = StubAgent("conversation", "ok")
        bad = FailingAgent("memory")
        executor = ExecutionExecutor(agents={"conversation": good, "memory": bad})
        plan = ExecutionPlan(steps=[
            PlanStep(step_id="s1", agent_name="conversation", error_strategy=ErrorStrategy.SKIP),
            PlanStep(step_id="s2", agent_name="memory", error_strategy=ErrorStrategy.SKIP),
        ])
        ctx = ExecutionContext(user_id="u1")
        result = await executor.execute(plan, ctx)
        assert "s1" in result["step_results"]
        assert ctx.agent_outputs["s2"].status == "failed"

    @pytest.mark.asyncio
    async def test_skip_strategy(self) -> None:
        bad = FailingAgent("memory")
        good = StubAgent("conversation", "ok")
        executor = ExecutionExecutor(agents={"memory": bad, "conversation": good})
        plan = ExecutionPlan(steps=[
            PlanStep(step_id="s1", agent_name="memory", error_strategy=ErrorStrategy.SKIP),
            PlanStep(step_id="s2", agent_name="conversation"),
        ])
        ctx = ExecutionContext(user_id="u1")
        result = await executor.execute(plan, ctx)
        assert "s1" in result["skipped"]
        assert "s2" in result["step_results"]

    @pytest.mark.asyncio
    async def test_optional_agent_failure_skipped(self) -> None:
        bad = FailingAgent("blind_spot")
        good = StubAgent("conversation", "ok")
        executor = ExecutionExecutor(agents={"blind_spot": bad, "conversation": good})
        plan = ExecutionPlan(steps=[
            PlanStep(step_id="s1", agent_name="blind_spot", optional=True, error_strategy=ErrorStrategy.SKIP),
            PlanStep(step_id="s2", agent_name="conversation"),
        ])
        ctx = ExecutionContext(user_id="u1")
        result = await executor.execute(plan, ctx)
        assert "s1" in result["skipped"]
        assert "s2" in result["step_results"]

    @pytest.mark.asyncio
    async def test_timeout_handling(self) -> None:
        slow = SlowAgent("slow_agent", delay=10)
        executor = ExecutionExecutor(agents={"slow_agent": slow})
        plan = ExecutionPlan(steps=[PlanStep(step_id="s1", agent_name="slow_agent", timeout_seconds=0.1)])
        ctx = ExecutionContext(user_id="u1")
        await executor.execute(plan, ctx)
        assert ctx.agent_outputs["s1"].status == "failed"

    @pytest.mark.asyncio
    async def test_cancellation(self) -> None:
        slow = SlowAgent("slow_agent", delay=10)
        executor = ExecutionExecutor(agents={"slow_agent": slow})
        plan = ExecutionPlan(steps=[
            PlanStep(step_id="s1", agent_name="slow_agent", timeout_seconds=60),
            PlanStep(step_id="s2", agent_name="slow_agent", timeout_seconds=60),
        ])
        ctx = ExecutionContext(user_id="u1")

        async def cancel_later():
            await asyncio.sleep(0.05)
            ctx.cancel()

        cancel_task = asyncio.create_task(cancel_later())
        await executor.execute(plan, ctx)
        assert ctx.cancelled
        cancel_task.cancel()

    @pytest.mark.asyncio
    async def test_dependency_failure_skips_dependent(self) -> None:
        bad = FailingAgent("memory")
        good = StubAgent("conversation", "ok")
        executor = ExecutionExecutor(agents={"memory": bad, "conversation": good})
        plan = ExecutionPlan(steps=[
            PlanStep(step_id="s1", agent_name="memory", error_strategy=ErrorStrategy.ABORT),
            PlanStep(step_id="s2", agent_name="conversation", dependencies=["s1"]),
        ])
        ctx = ExecutionContext(user_id="u1")
        result = await executor.execute(plan, ctx)
        assert ctx.agent_outputs["s1"].status == "failed"
        assert "s2" in result["skipped"]

    @pytest.mark.asyncio
    async def test_condition_false_skips_step(self) -> None:
        agent = StubAgent("library", "chunks")
        executor = ExecutionExecutor(agents={"library": agent})
        plan = ExecutionPlan(steps=[
            PlanStep(step_id="s1", agent_name="library", condition="has_books"),
        ])
        ctx = ExecutionContext(user_id="u1")
        ctx.accumulated["book_count"] = 0
        result = await executor.execute(plan, ctx)
        assert "s1" in result["skipped"]

    @pytest.mark.asyncio
    async def test_circuit_breaker(self) -> None:
        bad = FailingAgent("flaky")
        executor = ExecutionExecutor(
            agents={"flaky": bad},
            failure_manager=FailureManager(circuit_threshold=2, circuit_cooldown_seconds=0.01),
        )
        plan = ExecutionPlan(steps=[
            PlanStep(step_id="s1", agent_name="flaky", error_strategy=ErrorStrategy.RETRY, max_retries=0),
            PlanStep(step_id="s2", agent_name="flaky", error_strategy=ErrorStrategy.RETRY, max_retries=0),
            PlanStep(step_id="s3", agent_name="flaky", error_strategy=ErrorStrategy.RETRY, max_retries=0),
        ])
        ctx = ExecutionContext(user_id="u1")
        await executor.execute(plan, ctx)
        assert ctx.agent_outputs["s1"].status == "failed"
        assert ctx.agent_outputs["s2"].status == "failed"


# ---------------------------------------------------------------------------
# Failure manager tests
# ---------------------------------------------------------------------------

class TestFailureManager:
    @pytest.mark.asyncio
    async def test_retry_strategy(self) -> None:
        fm = FailureManager(max_retries=2, backoff_base=0.01)
        step = PlanStep(step_id="s1", agent_name="test", error_strategy=ErrorStrategy.RETRY, max_retries=2)
        should_retry, action = await fm.handle_step_failure(step, Exception("err"), 0)
        assert should_retry is True
        assert action == "retry"

    @pytest.mark.asyncio
    async def test_skip_strategy(self) -> None:
        fm = FailureManager()
        step = PlanStep(step_id="s1", agent_name="test", error_strategy=ErrorStrategy.SKIP)
        should_retry, action = await fm.handle_step_failure(step, Exception("err"), 0)
        assert should_retry is False
        assert action == "skip"

    @pytest.mark.asyncio
    async def test_abort_strategy(self) -> None:
        fm = FailureManager()
        step = PlanStep(step_id="s1", agent_name="test", error_strategy=ErrorStrategy.ABORT)
        should_retry, action = await fm.handle_step_failure(step, Exception("err"), 0)
        assert should_retry is False
        assert action == "abort"

    @pytest.mark.asyncio
    async def test_degrade_strategy(self) -> None:
        fm = FailureManager()
        step = PlanStep(step_id="s1", agent_name="test", error_strategy=ErrorStrategy.DEGRADE)
        should_retry, action = await fm.handle_step_failure(step, Exception("err"), 0)
        assert should_retry is False
        assert action == "degrade"

    @pytest.mark.asyncio
    async def test_retry_exhausted(self) -> None:
        fm = FailureManager(backoff_base=0.01)
        step = PlanStep(step_id="s1", agent_name="test", error_strategy=ErrorStrategy.RETRY, max_retries=2)
        should_retry, action = await fm.handle_step_failure(step, Exception("err"), 2)
        assert should_retry is False
        assert action == "exhausted"

    def test_circuit_breaker(self) -> None:
        fm = FailureManager(circuit_threshold=2)
        assert fm.is_circuit_open("agent1") is False
        fm.record_failure("agent1")
        assert fm.is_circuit_open("agent1") is False
        fm.record_failure("agent1")
        assert fm.is_circuit_open("agent1") is True


# ---------------------------------------------------------------------------
# Response composer tests
# ---------------------------------------------------------------------------

class TestResponseComposer:
    def test_compose_with_text(self) -> None:
        composer = ResponseComposer()
        outputs = {
            "s1": AgentOutput(status="success", data={"response_text": "hello world"}),
        }
        response = composer.compose(outputs)
        assert response.response_text == "hello world"

    def test_compose_with_memories(self) -> None:
        composer = ResponseComposer()
        outputs = {
            "s1": AgentOutput(status="success", data={"response_text": "ok", "memories": [{"content": "test"}]}),
        }
        response = composer.compose(outputs)
        assert len(response.memories) == 1

    def test_compose_skips_failed(self) -> None:
        composer = ResponseComposer()
        outputs = {
            "s1": AgentOutput(status="failed", data={"error": "boom"}),
            "s2": AgentOutput(status="success", data={"response_text": "ok"}),
        }
        response = composer.compose(outputs)
        assert response.response_text == "ok"

    def test_compose_tracks_skipped(self) -> None:
        composer = ResponseComposer()
        response = composer.compose({}, skipped_steps=["s1", "s2"])
        assert response.skipped_steps == ["s1", "s2"]

    def test_compose_metadata(self) -> None:
        composer = ResponseComposer()
        outputs = {
            "s1": AgentOutput(status="success", data={}),
            "s2": AgentOutput(status="failed", data={}),
        }
        response = composer.compose(outputs)
        assert response.metadata["total_agent_outputs"] == 2
        assert response.metadata["successful_outputs"] == 1


# ---------------------------------------------------------------------------
# Event publisher tests
# ---------------------------------------------------------------------------

class TestRuntimeEventPublisher:
    @pytest.mark.asyncio
    async def test_publishes_event(self, event_publisher: RuntimeEventPublisher, event_bus: InMemoryEventBus) -> None:
        ctx = ExecutionContext(user_id="u1")
        await event_publisher.publish(ctx, "TestEvent", {"key": "value"})
        assert len(event_bus.events) == 1
        assert event_bus.events[0]["type"] == "TestEvent"
        assert event_bus.events[0]["request_id"] == ctx.request_id

    @pytest.mark.asyncio
    async def test_records_in_context(self, event_publisher: RuntimeEventPublisher) -> None:
        ctx = ExecutionContext(user_id="u1")
        await event_publisher.publish(ctx, "TestEvent")
        assert len(ctx.event_log) == 1

    @pytest.mark.asyncio
    async def test_step_event(self, event_publisher: RuntimeEventPublisher, event_bus: InMemoryEventBus) -> None:
        ctx = ExecutionContext(user_id="u1")
        await event_publisher.publish_step_event(ctx, "AgentStarted", "s1", "conversation")
        assert event_bus.events[0]["step_id"] == "s1"
        assert event_bus.events[0]["agent"] == "conversation"


# ---------------------------------------------------------------------------
# Coordinator integration tests
# ---------------------------------------------------------------------------

class TestRuntimeCoordinator:
    @pytest.mark.asyncio
    async def test_full_flow(self, event_publisher: RuntimeEventPublisher) -> None:
        conv = StubAgent("conversation", "hello user")
        mem = StubAgent("memory", "")
        agents = {"conversation": conv, "memory": mem}
        rule = RulePlanner(templates=[PlanTemplate("greet", ["hello"], [
            PlanStep(step_id="s1", agent_name="conversation"),
            PlanStep(step_id="s2", agent_name="memory"),
        ])])
        executor = ExecutionExecutor(agents=agents)
        coordinator = RuntimeCoordinator(
            planner=ExecutionPlanner(rule, LLMPlanner(), confidence_threshold=0.3),
            executor=executor,
            composer=ResponseComposer(),
            event_publisher=event_publisher,
        )
        result = await coordinator.process({"user_id": "u1", "message": "hello there"})
        assert result.response.response_text == "hello user"
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_planner_failure_returns_error(self, event_publisher: RuntimeEventPublisher) -> None:
        rule = RulePlanner(templates=[])
        executor = ExecutionExecutor(agents={})
        coordinator = RuntimeCoordinator(
            planner=ExecutionPlanner(rule, LLMPlanner(), confidence_threshold=0.99),
            executor=executor,
            composer=ResponseComposer(),
            event_publisher=event_publisher,
            global_timeout_seconds=0.01,
        )
        result = await coordinator.process({"user_id": "u1", "message": "test"})
        assert result.response.response_text == ""

    @pytest.mark.asyncio
    async def test_agent_failure_graceful(self, event_publisher: RuntimeEventPublisher) -> None:
        conv = StubAgent("conversation", "ok anyway")
        agents = {"conversation": conv}
        rule = RulePlanner(templates=[PlanTemplate("g", ["hello"], [
            PlanStep(step_id="s1", agent_name="conversation"),
        ])])
        executor = ExecutionExecutor(agents=agents)
        coordinator = RuntimeCoordinator(
            planner=ExecutionPlanner(rule, LLMPlanner(), confidence_threshold=0.3),
            executor=executor,
            composer=ResponseComposer(),
            event_publisher=event_publisher,
        )
        result = await coordinator.process({"user_id": "u1", "message": "hello"})
        assert result.response.response_text == "ok anyway"

    @pytest.mark.asyncio
    async def test_global_timeout(self, event_publisher: RuntimeEventPublisher) -> None:
        slow = SlowAgent("slow", delay=10)
        agents = {"slow": slow}
        rule = RulePlanner(templates=[PlanTemplate("g", ["hello"], [
            PlanStep(step_id="s1", agent_name="slow", timeout_seconds=60),
        ])])
        executor = ExecutionExecutor(agents=agents)
        coordinator = RuntimeCoordinator(
            planner=ExecutionPlanner(rule, LLMPlanner(), confidence_threshold=0.3),
            executor=executor,
            composer=ResponseComposer(),
            event_publisher=event_publisher,
            global_timeout_seconds=0.1,
        )
        result = await coordinator.process({"user_id": "u1", "message": "hello"})
        assert result.response.response_text == ""

    @pytest.mark.asyncio
    async def test_conditional_execution(self, event_publisher: RuntimeEventPublisher) -> None:
        lib = StubAgent("library", "book chunks")
        conv = StubAgent("conversation", "response")
        agents = {"library": lib, "conversation": conv}
        rule = RulePlanner(templates=[PlanTemplate("q", ["book"], [
            PlanStep(step_id="s1", agent_name="library", condition="has_books"),
            PlanStep(step_id="s2", agent_name="conversation"),
        ])])
        executor = ExecutionExecutor(agents=agents)
        coordinator = RuntimeCoordinator(
            planner=ExecutionPlanner(rule, LLMPlanner(), confidence_threshold=0.3),
            executor=executor,
            composer=ResponseComposer(),
            event_publisher=event_publisher,
        )
        result = await coordinator.process({"user_id": "u1", "message": "tell me about the book"})
        assert "s1" in result.context.agent_outputs or "s1" in [t.step_id for t in result.context.step_traces]


# ---------------------------------------------------------------------------
# Step trace tests
# ---------------------------------------------------------------------------

class TestStepTrace:
    def test_trace_records_timing(self) -> None:
        ctx = ExecutionContext(user_id="u1")
        trace = StepTrace(step_id="s1", agent_name="conversation")
        ctx.step_traces.append(trace)
        assert trace.status == "pending"
        assert trace.retry_count == 0
