"""Comprehensive tests for the ReflectionAgent."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from ayeneh.agents.reflection import (
    KnowledgeRetriever,
    LLMGateway,
    PromptBuilder,
    ReflectionAgent,
    ReflectionConfig,
    ReflectionOutput,
    ReflectionRepository,
)
from ayeneh.application.services.memory import Memory, MemoryType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_memory(
    content: str,
    user_id: uuid.UUID | None = None,
    days_ago: int = 0,
    confidence: float = 0.6,
    mem_type: MemoryType = MemoryType.SEMANTIC,
) -> Memory:
    return Memory(
        id=uuid.uuid4(),
        user_id=user_id or uuid.uuid4(),
        type=mem_type,
        content=content,
        confidence=confidence,
        created_at=datetime.now(UTC) - timedelta(days=days_ago),
    )


class FakeLLMGateway(LLMGateway):
    def __init__(self, response: str | None = None, fail: bool = False) -> None:
        self._response = response or json.dumps({
            "title": "Reflection on Growth",
            "summary": "The user has shown consistent growth in self-awareness.",
            "supporting_evidence": [{"memory_id": "m1", "content": "growth evidence"}],
            "related_patterns": [{"name": "growth_pattern", "description": "shows growth"}],
            "related_memories": [{"id": "m1", "content": "growth memory"}],
            "supporting_citations": [{"source": "book", "excerpt": "growth excerpt"}],
            "confidence": 0.7,
            "actionable_questions": ["What further growth is possible?"],
            "limitations": ["Limited data span"],
            "strengths": ["Consistent self-reflection"],
            "growth_areas": ["Deeper introspection"],
            "unresolved_questions": ["What drives the growth?"],
        })
        self._fail = fail
        self.call_count = 0

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        self.call_count += 1
        if self._fail:
            raise ConnectionError("LLM unavailable")
        return {"choices": [{"message": {"content": self._response}}], "usage": {}}


class FakePromptBuilder(PromptBuilder):
    async def build(self, task_type: str, **kwargs: Any) -> dict[str, Any]:
        return {"messages": [{"role": "system", "content": "reflect"}, {"role": "user", "content": "analyze"}]}


class FakeReflectionRepo(ReflectionRepository):
    def __init__(self) -> None:
        self.stored: list[dict[str, Any]] = []

    async def create(self, reflection: dict[str, Any]) -> dict[str, Any]:
        self.stored.append(reflection)
        return reflection

    async def list_by_user(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        return []


class FakeKnowledgeRetriever(KnowledgeRetriever):
    def __init__(self, chunks: list[dict[str, Any]] | None = None) -> None:
        self._chunks = chunks or []
        self.call_count = 0

    async def search(self, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
        self.call_count += 1
        return self._chunks[:limit]


@pytest.fixture
def uid() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def repo() -> FakeReflectionRepo:
    return FakeReflectionRepo()


@pytest.fixture
def llm() -> FakeLLMGateway:
    return FakeLLMGateway()


@pytest.fixture
def knowledge() -> FakeKnowledgeRetriever:
    return FakeKnowledgeRetriever()


@pytest.fixture
def agent(llm: FakeLLMGateway, repo: FakeReflectionRepo, knowledge: FakeKnowledgeRetriever) -> ReflectionAgent:
    return ReflectionAgent(llm=llm, prompt_builder=FakePromptBuilder(), reflection_repo=repo, knowledge_retriever=knowledge)


# ---------------------------------------------------------------------------
# Reflection generation
# ---------------------------------------------------------------------------

class TestReflectionGeneration:
    @pytest.mark.asyncio
    async def test_generates_reflection(self, agent: ReflectionAgent, uid: uuid.UUID) -> None:
        memories = [
            _make_memory("I feel grateful for my family", uid, days_ago=30),
            _make_memory("I've been reading more lately", uid, days_ago=15),
            _make_memory("I noticed I'm more patient now", uid, days_ago=1),
        ]
        output = await agent.execute({"user_id": str(uid), "semantic_memories": [
            {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
            for m in memories
        ]})
        assert output.status == "success"
        assert output.data["reflection"].get("title") or output.data.get("title")

    @pytest.mark.asyncio
    async def test_fallback_without_llm(self) -> None:
        agent = ReflectionAgent(llm=None, prompt_builder=FakePromptBuilder(), reflection_repo=FakeReflectionRepo())
        memories = [
            _make_memory("I feel grateful", uuid.uuid4(), days_ago=30),
            _make_memory("I've grown this year", uuid.uuid4(), days_ago=15),
            _make_memory("I'm more patient now", uuid.uuid4(), days_ago=1),
        ]
        output = await agent.execute({"user_id": str(uuid.uuid4()), "semantic_memories": [
            {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
            for m in memories
        ]})
        assert output.status == "success"
        assert output.data["reflection"].get("summary")


# ---------------------------------------------------------------------------
# Evidence linking
# ---------------------------------------------------------------------------

class TestEvidenceLinking:
    @pytest.mark.asyncio
    async def test_evidence_included(self, agent: ReflectionAgent, uid: uuid.UUID) -> None:
        memories = [
            _make_memory("I value family above all else", uid, days_ago=30),
            _make_memory("Reading has changed my perspective", uid, days_ago=15),
            _make_memory("I feel calmer than before", uid, days_ago=1),
        ]
        output = await agent.execute({"user_id": str(uid), "semantic_memories": [
            {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
            for m in memories
        ]})
        assert output.status == "success"
        assert output.metadata["evidence_count"] >= 1


# ---------------------------------------------------------------------------
# Citation linking
# ---------------------------------------------------------------------------

class TestCitationLinking:
    @pytest.mark.asyncio
    async def test_knowledge_retrieved(self, knowledge: FakeKnowledgeRetriever) -> None:
        knowledge._chunks = [{"content": "relevant passage", "score": 0.8}]
        agent = ReflectionAgent(llm=FakeLLMGateway(), reflection_repo=FakeReflectionRepo(), knowledge_retriever=knowledge)
        memories = [_make_memory("I value reading", uuid.uuid4(), days_ago=30)] * 3
        await agent.execute({"user_id": str(uuid.uuid4()), "semantic_memories": [
            {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
            for m in memories
        ]})
        assert knowledge.call_count >= 1


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

class TestConfidenceScoring:
    @pytest.mark.asyncio
    async def test_higher_evidence_higher_confidence(self, agent: ReflectionAgent, uid: uuid.UUID) -> None:
        few = [_make_memory("I like cats", uid, days_ago=10)] * 3
        many = [_make_memory("I like cats", uid, days_ago=30)] * 10
        out_few = await agent.execute({"user_id": str(uid), "semantic_memories": [
            {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
            for m in few
        ]})
        out_many = await agent.execute({"user_id": str(uid), "semantic_memories": [
            {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
            for m in many
        ]})
        assert out_many.metadata.get("confidence", 0) >= out_few.metadata.get("confidence", 0)


# ---------------------------------------------------------------------------
# Uncertainty handling
# ---------------------------------------------------------------------------

class TestUncertaintyHandling:
    @pytest.mark.asyncio
    async def test_low_data_reflection(self, agent: ReflectionAgent, uid: uuid.UUID) -> None:
        memories = [_make_memory("I like reading", uid, days_ago=10)] * 3
        output = await agent.execute({"user_id": str(uid), "semantic_memories": [
            {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
            for m in memories
        ]})
        assert output.status == "success"


# ---------------------------------------------------------------------------
# Missing knowledge
# ---------------------------------------------------------------------------

class TestMissingKnowledge:
    @pytest.mark.asyncio
    async def test_no_knowledge_still_reflects(self) -> None:
        agent = ReflectionAgent(llm=FakeLLMGateway(), reflection_repo=FakeReflectionRepo(), knowledge_retriever=None)
        memories = [_make_memory("I value honesty", uuid.uuid4(), days_ago=30)] * 3
        output = await agent.execute({"user_id": str(uuid.uuid4()), "semantic_memories": [
            {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
            for m in memories
        ]})
        assert output.status == "success"

    @pytest.mark.asyncio
    async def test_knowledge_failure_graceful(self) -> None:
        class FailingKnowledge(KnowledgeRetriever):
            async def search(self, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
                raise ConnectionError("knowledge unavailable")

        agent = ReflectionAgent(llm=FakeLLMGateway(), reflection_repo=FakeReflectionRepo(), knowledge_retriever=FailingKnowledge())
        memories = [_make_memory("I value honesty", uuid.uuid4(), days_ago=30)] * 3
        output = await agent.execute({"user_id": str(uuid.uuid4()), "semantic_memories": [
            {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
            for m in memories
        ]})
        assert output.status == "success"


# ---------------------------------------------------------------------------
# Missing memories / patterns
# ---------------------------------------------------------------------------

class TestMissingEvidence:
    @pytest.mark.asyncio
    async def test_insufficient_evidence(self, agent: ReflectionAgent, uid: uuid.UUID) -> None:
        memories = [_make_memory("I like coffee", uid)]
        output = await agent.execute({"user_id": str(uid), "semantic_memories": [
            {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
            for m in memories
        ]})
        assert output.status == "success"
        assert output.metadata.get("reasoning", "").startswith("Insufficient")

    @pytest.mark.asyncio
    async def test_no_memories_no_patterns(self, agent: ReflectionAgent, uid: uuid.UUID) -> None:
        output = await agent.execute({"user_id": str(uid)})
        assert output.status == "success"


# ---------------------------------------------------------------------------
# LLM failure
# ---------------------------------------------------------------------------

class TestLLMFailure:
    @pytest.mark.asyncio
    async def test_llm_failure_fallback(self) -> None:
        agent = ReflectionAgent(llm=FakeLLMGateway(fail=True), reflection_repo=FakeReflectionRepo())
        memories = [_make_memory("I value honesty", uuid.uuid4(), days_ago=30)] * 3
        output = await agent.execute({"user_id": str(uuid.uuid4()), "semantic_memories": [
            {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
            for m in memories
        ]})
        assert output.status == "success"
        assert output.data["reflection"].get("summary")


# ---------------------------------------------------------------------------
# Validation failures
# ---------------------------------------------------------------------------

class TestValidationFailures:
    @pytest.mark.asyncio
    async def test_no_user_id(self, agent: ReflectionAgent) -> None:
        output = await agent.execute({})
        assert output.status == "failed"

    @pytest.mark.asyncio
    async def test_empty_llm_response(self) -> None:
        agent = ReflectionAgent(llm=FakeLLMGateway(response=""), reflection_repo=FakeReflectionRepo())
        memories = [_make_memory("I value honesty", uuid.uuid4(), days_ago=30)] * 3
        output = await agent.execute({"user_id": str(uuid.uuid4()), "semantic_memories": [
            {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
            for m in memories
        ]})
        assert output.status == "success"


# ---------------------------------------------------------------------------
# Scheduled vs on-demand
# ---------------------------------------------------------------------------

class TestExecutionModes:
    @pytest.mark.asyncio
    async def test_on_demand_with_context(self, agent: ReflectionAgent, uid: uuid.UUID) -> None:
        memories = [_make_memory("I value growth", uid, days_ago=30)] * 3
        output = await agent.execute({
            "user_id": str(uid),
            "semantic_memories": [
                {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
                for m in memories
            ],
            "execution_mode": "on_demand",
        })
        assert output.status == "success"

    @pytest.mark.asyncio
    async def test_scheduled_execution(self, agent: ReflectionAgent, uid: uuid.UUID) -> None:
        memories = [_make_memory("I value growth", uid, days_ago=30)] * 3
        output = await agent.execute({
            "user_id": str(uid),
            "semantic_memories": [
                {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
                for m in memories
            ],
            "execution_mode": "scheduled",
        })
        assert output.status == "success"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_events_emitted(self, agent: ReflectionAgent, uid: uuid.UUID) -> None:
        memories = [_make_memory("I value growth", uid, days_ago=30)] * 3
        output = await agent.execute({"user_id": str(uid), "semantic_memories": [
            {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
            for m in memories
        ]})
        assert len(output.events) >= 1

    @pytest.mark.asyncio
    async def test_metadata_complete(self, agent: ReflectionAgent, uid: uuid.UUID) -> None:
        memories = [_make_memory("I value growth", uid, days_ago=30)] * 3
        output = await agent.execute({"user_id": str(uid), "semantic_memories": [
            {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
            for m in memories
        ]})
        assert "evidence_count" in output.metadata
        assert "memory_count" in output.metadata
        assert "latency_ms" in output.metadata

    @pytest.mark.asyncio
    async def test_with_patterns(self, agent: ReflectionAgent, uid: uuid.UUID) -> None:
        memories = [_make_memory("I value growth", uid, days_ago=30)] * 3
        patterns = [{"name": "growth_pattern", "description": "shows growth", "trend": "increasing"}]
        output = await agent.execute({
            "user_id": str(uid),
            "semantic_memories": [
                {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
                for m in memories
            ],
            "patterns": patterns,
        })
        assert output.status == "success"
        assert output.metadata["pattern_count"] == 1

    @pytest.mark.asyncio
    async def test_with_existing_reflections(self, agent: ReflectionAgent, uid: uuid.UUID) -> None:
        memories = [_make_memory("I value growth", uid, days_ago=30)] * 3
        existing = [{"title": "Previous reflection"}]
        output = await agent.execute({
            "user_id": str(uid),
            "semantic_memories": [
                {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
                for m in memories
            ],
            "existing_reflections": existing,
        })
        assert output.status == "success"

    @pytest.mark.asyncio
    async def test_no_repo_still_works(self) -> None:
        agent = ReflectionAgent(llm=FakeLLMGateway(), reflection_repo=None)
        memories = [_make_memory("I value growth", uuid.uuid4(), days_ago=30)] * 3
        output = await agent.execute({"user_id": str(uuid.uuid4()), "semantic_memories": [
            {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
            for m in memories
        ]})
        assert output.status == "success"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

class TestDataclasses:
    def test_reflection_config_defaults(self) -> None:
        c = ReflectionConfig()
        assert c.min_memories == 3
        assert c.min_patterns == 1
        assert c.min_confidence == 0.3

    def test_reflection_output_defaults(self) -> None:
        r = ReflectionOutput()
        assert r.title == ""
        assert r.confidence == 0.5
        assert r.strengths == []
