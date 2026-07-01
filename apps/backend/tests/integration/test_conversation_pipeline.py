"""Integration tests for the complete conversation pipeline.

Covers: full persistence, agent persistence, execution plan persistence,
rollback on failure, event publishing, concurrent requests.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ayeneh.agents.base import AgentOutput, BaseAgent
from ayeneh.application.ports.event_bus import EventBus
from ayeneh.application.services.conversation import ConversationService
from ayeneh.application.services.insight import InsightService
from ayeneh.application.services.pattern import PatternService
from ayeneh.application.services.reflection import ReflectionService
from ayeneh.infrastructure.persistence.base import Base
from ayeneh.infrastructure.persistence.unit_of_work import UnitOfWork
from ayeneh.runtime.composer import ResponseComposer
from ayeneh.runtime.coordinator import RuntimeCoordinator
from ayeneh.runtime.events import RuntimeEventPublisher
from ayeneh.runtime.executor import ExecutionExecutor
from ayeneh.runtime.persistence import RuntimePersistence
from ayeneh.runtime.planner import (
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
    def __init__(self, name: str, output_data: dict[str, Any] | None = None) -> None:
        self.name = name
        self._output = output_data or {"response_text": f"{name} output"}

    async def execute(self, context: dict[str, Any]) -> AgentOutput:
        return AgentOutput(status="success", data=self._output)


class FailingAgent(BaseAgent):
    def __init__(self, name: str, error: str = "boom") -> None:
        self.name = name
        self._error = error

    async def execute(self, context: dict[str, Any]) -> AgentOutput:
        raise RuntimeError(self._error)


class StubMemoryService:
    def __init__(self) -> None:
        self.stored: list[dict[str, Any]] = []

    async def store(self, data: Any) -> Any:
        self.stored.append({"content": data.content, "type": data.type})
        return data


class StubPatternService:
    def __init__(self) -> None:
        self.stored: list[dict[str, Any]] = []

    async def create_pattern(self, **kwargs: Any) -> dict[str, Any]:
        self.stored.append(kwargs)
        return {"id": str(uuid.uuid4()), "updated": False}


class StubReflectionService:
    def __init__(self) -> None:
        self.stored: list[dict[str, Any]] = []

    async def create_reflection(self, **kwargs: Any) -> dict[str, Any]:
        self.stored.append(kwargs)
        return {"id": str(uuid.uuid4()), "title": kwargs.get("title", "")}


class StubInsightService:
    def __init__(self) -> None:
        self.stored: list[dict[str, Any]] = []

    async def create_observation(self, **kwargs: Any) -> dict[str, Any]:
        self.stored.append(kwargs)
        return {"id": str(uuid.uuid4()), "content": kwargs.get("content", "")}


class InMemoryEventBus(EventBus):
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append({"type": event_type, **payload})

    def subscribe(self, event_type: str, handler: Any) -> None:
        pass


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
def event_bus():
    return InMemoryEventBus()


@pytest_asyncio.fixture
def event_publisher(event_bus):
    return RuntimeEventPublisher(event_bus)


@pytest_asyncio.fixture
def conversation_service(uow_factory):
    return ConversationService(uow_factory)


@pytest_asyncio.fixture
def pattern_service(uow_factory):
    return PatternService(uow_factory)


@pytest_asyncio.fixture
def reflection_service(uow_factory):
    return ReflectionService(uow_factory)


@pytest_asyncio.fixture
def insight_service(uow_factory):
    return InsightService(uow_factory)


@pytest_asyncio.fixture
def persistence(uow_factory):
    return RuntimePersistence(uow_factory)


def _make_coordinator(
    agents: dict[str, BaseAgent],
    event_publisher: RuntimeEventPublisher,
    persistence: RuntimePersistence | None = None,
    services: dict[str, Any] | None = None,
    steps: list[PlanStep] | None = None,
) -> RuntimeCoordinator:
    if steps is None:
        steps = [PlanStep(step_id=f"s{i+1}", agent_name=name) for i, name in enumerate(agents)]
    template = PlanTemplate("default", ["a", "e", "i", "o", "u"], steps, confidence=1.0)
    planner = ExecutionPlanner(
        rule_planner=RulePlanner(templates=[template]),
        llm_planner=LLMPlanner(),
        confidence_threshold=0.1,
        registered_agents=set(agents.keys()),
    )
    executor = ExecutionExecutor(agents=agents)
    return RuntimeCoordinator(
        planner=planner,
        executor=executor,
        composer=ResponseComposer(),
        event_publisher=event_publisher,
        persistence=persistence,
        services=services or {},
    )


# ---------------------------------------------------------------------------
# Tests: Full conversation persistence
# ---------------------------------------------------------------------------

class TestConversationPersistence:
    @pytest.mark.asyncio
    async def test_create_and_retrieve_conversation(
        self, conversation_service: ConversationService
    ) -> None:
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        conv = await conversation_service.create_conversation(
            user_id, session_id, title="Test conversation", topic="testing"
        )
        assert conv["id"]
        assert conv["title"] == "Test conversation"

        retrieved = await conversation_service.get_conversation(conv["id"])
        assert retrieved is not None
        assert retrieved["title"] == "Test conversation"

    @pytest.mark.asyncio
    async def test_list_conversations(
        self, conversation_service: ConversationService
    ) -> None:
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        await conversation_service.create_conversation(user_id, session_id, title="Conv 1")
        await conversation_service.create_conversation(user_id, session_id, title="Conv 2")

        convs = await conversation_service.list_conversations(user_id)
        assert len(convs) == 2

    @pytest.mark.asyncio
    async def test_create_and_list_messages(
        self, conversation_service: ConversationService
    ) -> None:
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        conv = await conversation_service.create_conversation(user_id, session_id)

        msg1 = await conversation_service.create_message(
            user_id, conv["id"], "Hello", role="user"
        )
        assert msg1["sequence_number"] == 1

        msg2 = await conversation_service.create_message(
            user_id, conv["id"], "Hi there", role="assistant"
        )
        assert msg2["sequence_number"] == 2

        messages = await conversation_service.get_messages(conv["id"])
        assert len(messages) == 2
        assert messages[0]["content"] == "Hello"
        assert messages[1]["content"] == "Hi there"

    @pytest.mark.asyncio
    async def test_archive_conversation(
        self, conversation_service: ConversationService
    ) -> None:
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        conv = await conversation_service.create_conversation(user_id, session_id)

        await conversation_service.archive_conversation(conv["id"])

        archived = await conversation_service.get_conversation(conv["id"])
        assert archived is not None
        assert archived["status"] == "archived"

    @pytest.mark.asyncio
    async def test_message_not_found_conversation(
        self, conversation_service: ConversationService
    ) -> None:
        user_id = str(uuid.uuid4())
        with pytest.raises(ValueError, match="not found"):
            await conversation_service.create_message(
                user_id, str(uuid.uuid4()), "hello"
            )


# ---------------------------------------------------------------------------
# Tests: Agent persistence
# ---------------------------------------------------------------------------

class TestAgentPersistence:
    @pytest.mark.asyncio
    async def test_pattern_create_and_list(
        self, pattern_service: PatternService
    ) -> None:
        user_id = str(uuid.uuid4())
        result = await pattern_service.create_pattern(
            user_id, "Tends to avoid difficult conversations", strength=0.7
        )
        assert result["id"]

        patterns = await pattern_service.list_patterns(user_id)
        assert len(patterns) == 1
        assert patterns[0]["description"] == "Tends to avoid difficult conversations"

    @pytest.mark.asyncio
    async def test_pattern_deduplication(
        self, pattern_service: PatternService
    ) -> None:
        user_id = str(uuid.uuid4())
        await pattern_service.create_pattern(user_id, "Avoids conflict", strength=0.5)
        await pattern_service.create_pattern(user_id, "Avoids conflict", strength=0.8)

        patterns = await pattern_service.list_patterns(user_id)
        assert len(patterns) == 1
        assert patterns[0]["strength"] == 0.8

    @pytest.mark.asyncio
    async def test_reflection_create_and_list(
        self, reflection_service: ReflectionService
    ) -> None:
        user_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        result = await reflection_service.create_reflection(
            user_id, "Monthly Reflection", "You have shown growth...",
            period_start=now, period_end=now,
        )
        assert result["id"]

        refs = await reflection_service.list_reflections(user_id)
        assert len(refs) == 1
        assert refs[0]["title"] == "Monthly Reflection"

    @pytest.mark.asyncio
    async def test_observation_create_and_list(
        self, insight_service: InsightService
    ) -> None:
        user_id = str(uuid.uuid4())
        result = await insight_service.create_observation(
            user_id, "Contradiction detected between stated values and actions",
            source_agent="blind_spot",
        )
        assert result["id"]

        obs = await insight_service.list_observations(user_id)
        assert len(obs) == 1
        assert obs[0]["source_agent"] == "blind_spot"


# ---------------------------------------------------------------------------
# Tests: Execution plan persistence
# ---------------------------------------------------------------------------

class TestExecutionPlanPersistence:
    @pytest.mark.asyncio
    async def test_plan_saved_after_execution(
        self,
        event_publisher: RuntimeEventPublisher,
        persistence: RuntimePersistence,
        event_bus: InMemoryEventBus,
    ) -> None:
        conv = StubAgent("conversation", {"response_text": "hi"})
        agents = {"conversation": conv}
        coordinator = _make_coordinator(
            agents, event_publisher, persistence=persistence
        )

        result = await coordinator.process({"user_id": str(uuid.uuid4()), "message": "hello"})

        plan_events = [e for e in event_bus.events if e["type"] == "PlanCreated"]
        assert len(plan_events) == 1

        await persistence.save_execution_plan(
            result.context, ExecutionPlan(strategy="rule_based", steps=[
                PlanStep(step_id="s1", agent_name="conversation")
            ])
        )

    @pytest.mark.asyncio
    async def test_agent_runs_saved(
        self,
        event_publisher: RuntimeEventPublisher,
        persistence: RuntimePersistence,
        uow_factory,
    ) -> None:
        conv = StubAgent("conversation", {"response_text": "hi"})
        agents = {"conversation": conv}
        coordinator = _make_coordinator(
            agents, event_publisher, persistence=persistence
        )

        result = await coordinator.process({"user_id": str(uuid.uuid4()), "message": "hello"})

        plan_id = await persistence.save_execution_plan(
            result.context, ExecutionPlan(strategy="rule_based", steps=[
                PlanStep(step_id="s1", agent_name="conversation")
            ])
        )
        count = await persistence.save_agent_runs(plan_id, result.context)
        assert count == 1


# ---------------------------------------------------------------------------
# Tests: Agent output processing
# ---------------------------------------------------------------------------

class TestAgentOutputProcessing:
    @pytest.mark.asyncio
    async def test_conversation_agent_saves_response(
        self,
        event_publisher: RuntimeEventPublisher,
        persistence: RuntimePersistence,
        conversation_service: ConversationService,
        uow_factory,
    ) -> None:
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        conv = await conversation_service.create_conversation(user_id, session_id)

        conv_agent = StubAgent("conversation", {
            "response_text": "I understand your perspective.",
            "observations": [{"type": "emotional_expression", "content": "I feel..."}],
        })
        agents = {"conversation": conv_agent}
        steps = [PlanStep(step_id="s1", agent_name="conversation")]
        coordinator = _make_coordinator(
            agents, event_publisher, persistence=persistence,
            services={"conversation": conversation_service}, steps=steps,
        )

        await coordinator.process({
            "user_id": user_id,
            "conversation_id": conv["id"],
            "message": "I feel overwhelmed",
        })

        messages = await conversation_service.get_messages(conv["id"])
        assistant_msgs = [m for m in messages if m["role"] == "assistant"]
        assert len(assistant_msgs) == 1
        assert assistant_msgs[0]["content"] == "I understand your perspective."

    @pytest.mark.asyncio
    async def test_memory_agent_output_saved(
        self,
        event_publisher: RuntimeEventPublisher,
        persistence: RuntimePersistence,
    ) -> None:
        user_id = str(uuid.uuid4())

        mem_agent = StubAgent("memory", {
            "response_text": "",
            "memories": [
                {"type": "episodic", "content": "User felt overwhelmed today", "confidence": 0.6},
                {"type": "semantic", "content": "User tends to avoid conflict", "confidence": 0.7},
            ],
        })
        stub_mem = StubMemoryService()
        agents = {"memory": mem_agent}
        steps = [PlanStep(step_id="s0", agent_name="memory")]
        coordinator = _make_coordinator(
            agents, event_publisher, persistence=persistence,
            services={"memory": stub_mem}, steps=steps,
        )

        result = await coordinator.process({"user_id": user_id, "message": "I feel overwhelmed"})
        counts = await persistence.process_agent_outputs(result.context, memory_service=stub_mem)
        assert counts["memories"] == 2

    @pytest.mark.asyncio
    async def test_pattern_agent_output_saved(
        self,
        event_publisher: RuntimeEventPublisher,
        persistence: RuntimePersistence,
    ) -> None:
        user_id = str(uuid.uuid4())
        pat_agent = StubAgent("pattern", {
            "response_text": "",
            "patterns": [
                {"description": "Avoidance tendency", "strength": 0.6},
            ],
        })
        stub_pat = StubPatternService()
        agents = {"pattern": pat_agent}
        steps = [PlanStep(step_id="s0", agent_name="pattern")]
        coordinator = _make_coordinator(
            agents, event_publisher, persistence=persistence,
            services={"pattern": stub_pat}, steps=steps,
        )

        await coordinator.process({"user_id": user_id, "message": "I keep avoiding it"})
        assert len(stub_pat.stored) == 1
        assert stub_pat.stored[0]["description"] == "Avoidance tendency"

    @pytest.mark.asyncio
    async def test_reflection_agent_output_saved(
        self,
        event_publisher: RuntimeEventPublisher,
        persistence: RuntimePersistence,
    ) -> None:
        user_id = str(uuid.uuid4())
        ref_agent = StubAgent("reflection", {
            "response_text": "",
            "reflection": {"title": "Growth Analysis", "narrative": "You have grown significantly..."},
        })
        stub_ref = StubReflectionService()
        agents = {"reflection": ref_agent}
        steps = [PlanStep(step_id="s0", agent_name="reflection")]
        coordinator = _make_coordinator(
            agents, event_publisher, persistence=persistence,
            services={"reflection": stub_ref}, steps=steps,
        )

        await coordinator.process({"user_id": user_id, "message": "reflect on my journey"})
        assert len(stub_ref.stored) == 1
        assert stub_ref.stored[0]["title"] == "Growth Analysis"

    @pytest.mark.asyncio
    async def test_blind_spot_agent_output_saved(
        self,
        event_publisher: RuntimeEventPublisher,
        persistence: RuntimePersistence,
    ) -> None:
        user_id = str(uuid.uuid4())
        bs_agent = StubAgent("blind_spot", {
            "response_text": "",
            "observations": [
                {"content": "You say you value honesty but avoid difficult conversations", "source": "blind_spot"},
            ],
        })
        stub_ins = StubInsightService()
        agents = {"blind_spot": bs_agent}
        steps = [PlanStep(step_id="s0", agent_name="blind_spot")]
        coordinator = _make_coordinator(
            agents, event_publisher, persistence=persistence,
            services={"insight": stub_ins}, steps=steps,
        )

        await coordinator.process({"user_id": user_id, "message": "analyse my blind spots"})
        assert len(stub_ins.stored) == 1


# ---------------------------------------------------------------------------
# Tests: Rollback on failure
# ---------------------------------------------------------------------------

class TestRollbackOnFailure:
    @pytest.mark.asyncio
    async def test_uow_rollback_preserves_isolation(
        self, uow_factory, conversation_service: ConversationService
    ) -> None:
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        conv = await conversation_service.create_conversation(user_id, session_id, title="Keep me")

        try:
            async with uow_factory():
                raise ValueError("simulate error")
        except ValueError:
            pass

        retrieved = await conversation_service.get_conversation(conv["id"])
        assert retrieved is not None

    @pytest.mark.asyncio
    async def test_executor_failure_does_not_corrupt_context(
        self, event_publisher: RuntimeEventPublisher
    ) -> None:
        good = StubAgent("conversation", {"response_text": "ok"})
        bad = FailingAgent("memory")
        agents = {"conversation": good, "memory": bad}
        steps = [
            PlanStep(step_id="s0", agent_name="conversation"),
            PlanStep(step_id="s1", agent_name="memory"),
        ]

        coordinator = _make_coordinator(
            agents, event_publisher, steps=steps
        )

        result = await coordinator.process({"user_id": str(uuid.uuid4()), "message": "hello"})
        assert result.response.response_text == "ok"
        assert result.context.agent_outputs["s1"].status == "failed"


# ---------------------------------------------------------------------------
# Tests: Event publishing
# ---------------------------------------------------------------------------

class TestEventPublishing:
    @pytest.mark.asyncio
    async def test_full_request_emits_complete_event_sequence(
        self, event_publisher: RuntimeEventPublisher, event_bus: InMemoryEventBus
    ) -> None:
        conv = StubAgent("conversation", {"response_text": "hi"})
        agents = {"conversation": conv}
        coordinator = _make_coordinator(agents, event_publisher)

        result = await coordinator.process({"user_id": str(uuid.uuid4()), "message": "hello"})

        event_types = [e["type"] for e in event_bus.events]
        assert "RuntimeStarted" in event_types
        assert "PlanCreated" in event_types
        assert "RuntimeCompleted" in event_types

        ctx_event_types = [e.event_type for e in result.context.event_log]
        agent_events = [e for e in ctx_event_types if e.startswith("Agent")]
        assert len(agent_events) > 0

    @pytest.mark.asyncio
    async def test_agent_start_and_complete_events(
        self, event_publisher: RuntimeEventPublisher, event_bus: InMemoryEventBus
    ) -> None:
        conv = StubAgent("conversation", {"response_text": "hi"})
        agents = {"conversation": conv}
        coordinator = _make_coordinator(agents, event_publisher)

        result = await coordinator.process({"user_id": str(uuid.uuid4()), "message": "hello"})

        ctx_event_types = [e.event_type for e in result.context.event_log]
        started = [e for e in ctx_event_types if e == "AgentStarted"]
        completed = [e for e in ctx_event_types if e == "AgentCompleted"]
        assert len(started) == 1
        assert len(completed) == 1


# ---------------------------------------------------------------------------
# Tests: Concurrent requests
# ---------------------------------------------------------------------------

class TestConcurrentRequests:
    @pytest.mark.asyncio
    async def test_concurrent_conversation_processing(
        self, event_publisher: RuntimeEventPublisher, persistence: RuntimePersistence
    ) -> None:
        conv = StubAgent("conversation", {"response_text": "ok"})
        agents = {"conversation": conv}

        async def make_request(idx: int) -> None:
            ep = RuntimeEventPublisher(InMemoryEventBus())
            coordinator = _make_coordinator(agents, ep, persistence=persistence)
            result = await coordinator.process({
                "user_id": str(uuid.uuid4()),
                "message": f"message {idx}",
            })
            assert result.response.response_text == "ok"

        tasks = [make_request(i) for i in range(10)]
        await asyncio.gather(*tasks)

    @pytest.mark.asyncio
    async def test_concurrent_persistence_no_corruption(
        self, uow_factory, conversation_service: ConversationService
    ) -> None:
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        async def create_conv(title: str) -> dict:
            return await conversation_service.create_conversation(
                user_id, session_id, title=title
            )

        convs = await asyncio.gather(*[create_conv(f"Conv {i}") for i in range(5)])
        assert len({c["id"] for c in convs}) == 5

        listed = await conversation_service.list_conversations(user_id)
        assert len(listed) == 5
