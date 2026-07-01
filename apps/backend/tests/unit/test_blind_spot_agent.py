"""Comprehensive tests for the BlindSpotAgent."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from ayeneh.agents.blind_spot import (
    BlindSpotAgent,
    BlindSpotConfig,
    BlindSpotOutput,
    BlindSpotRepository,
    KnowledgeRetriever,
    LLMGateway,
    PromptBuilder,
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
        self._response = response or json.dumps([
            {
                "title": "Mixed signals in self-report",
                "description": "User shows both positive and negative emotions",
                "supporting_evidence": [{"memory_id": "m1", "content": "mixed evidence"}],
                "confidence": 0.6,
                "alternative_interpretations": ["Different contexts"],
                "reflective_questions": ["What triggers each feeling?"],
                "limitations": ["Limited data"],
                "severity": "medium",
            }
        ])
        self._fail = fail
        self.call_count = 0

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        self.call_count += 1
        if self._fail:
            raise ConnectionError("LLM unavailable")
        return {"choices": [{"message": {"content": self._response}}], "usage": {}}


class FakePromptBuilder(PromptBuilder):
    async def build(self, task_type: str, **kwargs: Any) -> dict[str, Any]:
        return {"messages": [{"role": "system", "content": "detect blind spots"}]}


class FakeBlindSpotRepo(BlindSpotRepository):
    def __init__(self) -> None:
        self.stored: list[dict[str, Any]] = []

    async def create(self, blind_spot: dict[str, Any]) -> dict[str, Any]:
        self.stored.append(blind_spot)
        return blind_spot

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
def repo() -> FakeBlindSpotRepo:
    return FakeBlindSpotRepo()


@pytest.fixture
def llm() -> FakeLLMGateway:
    return FakeLLMGateway()


@pytest.fixture
def knowledge() -> FakeKnowledgeRetriever:
    return FakeKnowledgeRetriever()


@pytest.fixture
def agent(llm: FakeLLMGateway, repo: FakeBlindSpotRepo, knowledge: FakeKnowledgeRetriever) -> BlindSpotAgent:
    return BlindSpotAgent(llm=llm, prompt_builder=FakePromptBuilder(), repo=repo, knowledge_retriever=knowledge)


# ---------------------------------------------------------------------------
# Blind spot generation
# ---------------------------------------------------------------------------

class TestBlindSpotGeneration:
    @pytest.mark.asyncio
    async def test_detects_contradictions(self, agent: BlindSpotAgent, uid: uuid.UUID) -> None:
        memories = [
            _make_memory("I feel happy and grateful today", uid, days_ago=1),
            _make_memory("I feel anxious and worried about work", uid, days_ago=3),
            _make_memory("I'm content with my life", uid, days_ago=5),
        ]
        output = await agent.execute({
            "user_id": str(uid),
            "semantic_memories": [
                {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
                for m in memories
            ],
        })
        assert output.status == "success"
        spots = output.data.get("blind_spots", [])
        assert len(spots) >= 1

    @pytest.mark.asyncio
    async def test_detects_avoidance_loops(self, agent: BlindSpotAgent, uid: uuid.UUID) -> None:
        memories = [
            _make_memory("I avoid confrontation at work", uid, days_ago=30),
            _make_memory("I keep avoiding the difficult conversation", uid, days_ago=20),
            _make_memory("I tend to postpone addressing issues", uid, days_ago=10),
        ]
        output = await agent.execute({
            "user_id": str(uid),
            "semantic_memories": [
                {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
                for m in memories
            ],
        })
        assert output.status == "success"
        spots = output.data.get("blind_spots", [])
        titles = [s["title"] for s in spots]
        assert any("avoidance" in t.lower() or "confrontation" in t.lower() for t in titles)


# ---------------------------------------------------------------------------
# Evidence grounding
# ---------------------------------------------------------------------------

class TestEvidenceGrounding:
    @pytest.mark.asyncio
    async def test_evidence_populated(self, agent: BlindSpotAgent, uid: uuid.UUID) -> None:
        memories = [
            _make_memory("I feel happy today", uid, days_ago=1),
            _make_memory("I feel stressed about tomorrow", uid, days_ago=3),
            _make_memory("I'm content overall", uid, days_ago=5),
        ]
        output = await agent.execute({
            "user_id": str(uid),
            "semantic_memories": [
                {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
                for m in memories
            ],
        })
        spots = output.data.get("blind_spots", [])
        for s in spots:
            assert len(s.get("supporting_evidence", [])) >= 1


# ---------------------------------------------------------------------------
# Alternative interpretations
# ---------------------------------------------------------------------------

class TestAlternativeInterpretations:
    @pytest.mark.asyncio
    async def test_alternatives_included(self, agent: BlindSpotAgent, uid: uuid.UUID) -> None:
        memories = [
            _make_memory("I feel happy today", uid, days_ago=1),
            _make_memory("I feel anxious about work", uid, days_ago=3),
            _make_memory("I'm content with family", uid, days_ago=5),
        ]
        output = await agent.execute({
            "user_id": str(uid),
            "semantic_memories": [
                {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
                for m in memories
            ],
        })
        spots = output.data.get("blind_spots", [])
        for s in spots:
            assert isinstance(s.get("alternative_interpretations", []), list)


# ---------------------------------------------------------------------------
# Uncertainty handling
# ---------------------------------------------------------------------------

class TestUncertaintyHandling:
    @pytest.mark.asyncio
    async def test_confidence_reported(self, agent: BlindSpotAgent, uid: uuid.UUID) -> None:
        memories = [
            _make_memory("I feel happy today", uid, days_ago=1),
            _make_memory("I feel anxious about work", uid, days_ago=3),
            _make_memory("I'm content with life", uid, days_ago=5),
        ]
        output = await agent.execute({
            "user_id": str(uid),
            "semantic_memories": [
                {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
                for m in memories
            ],
        })
        spots = output.data.get("blind_spots", [])
        for s in spots:
            assert 0.0 <= s.get("confidence", 0) <= 1.0


# ---------------------------------------------------------------------------
# Missing knowledge
# ---------------------------------------------------------------------------

class TestMissingKnowledge:
    @pytest.mark.asyncio
    async def test_no_knowledge_still_detects(self) -> None:
        agent = BlindSpotAgent(llm=FakeLLMGateway(), prompt_builder=FakePromptBuilder(), repo=FakeBlindSpotRepo(), knowledge_retriever=None)
        memories = [
            _make_memory("I feel happy today", user_id=uuid.uuid4(), days_ago=1),
            _make_memory("I feel anxious about work", user_id=uuid.uuid4(), days_ago=3),
            _make_memory("I'm content overall", user_id=uuid.uuid4(), days_ago=5),
        ]
        output = await agent.execute({
            "user_id": str(uuid.uuid4()),
            "semantic_memories": [
                {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
                for m in memories
            ],
        })
        assert output.status == "success"

    @pytest.mark.asyncio
    async def test_knowledge_failure_graceful(self) -> None:
        class FailingKnowledge(KnowledgeRetriever):
            async def search(self, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
                raise ConnectionError("knowledge unavailable")

        agent = BlindSpotAgent(llm=FakeLLMGateway(), prompt_builder=FakePromptBuilder(), repo=FakeBlindSpotRepo(), knowledge_retriever=FailingKnowledge())
        memories = [
            _make_memory("I feel happy today", user_id=uuid.uuid4(), days_ago=1),
            _make_memory("I feel anxious about work", user_id=uuid.uuid4(), days_ago=3),
            _make_memory("I'm content overall", user_id=uuid.uuid4(), days_ago=5),
        ]
        output = await agent.execute({
            "user_id": str(uuid.uuid4()),
            "semantic_memories": [
                {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
                for m in memories
            ],
        })
        assert output.status == "success"


# ---------------------------------------------------------------------------
# Missing reflections / patterns
# ---------------------------------------------------------------------------

class TestMissingEvidence:
    @pytest.mark.asyncio
    async def test_no_reflections_no_patterns(self, agent: BlindSpotAgent, uid: uuid.UUID) -> None:
        memories = [_make_memory("I feel happy today", uid, days_ago=1)] * 3
        output = await agent.execute({
            "user_id": str(uid),
            "semantic_memories": [
                {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
                for m in memories
            ],
        })
        assert output.status == "success"

    @pytest.mark.asyncio
    async def test_insufficient_evidence(self, agent: BlindSpotAgent, uid: uuid.UUID) -> None:
        memories = [_make_memory("I like coffee", uid)]
        output = await agent.execute({
            "user_id": str(uid),
            "semantic_memories": [
                {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
                for m in memories
            ],
        })
        assert output.status == "success"
        assert output.data.get("total_detected", 0) == 0


# ---------------------------------------------------------------------------
# LLM failures
# ---------------------------------------------------------------------------

class TestLLMFailure:
    @pytest.mark.asyncio
    async def test_llm_failure_still_detects(self) -> None:
        agent = BlindSpotAgent(llm=FakeLLMGateway(fail=True), prompt_builder=FakePromptBuilder(), repo=FakeBlindSpotRepo())
        memories = [
            _make_memory("I feel happy today", user_id=uuid.uuid4(), days_ago=1),
            _make_memory("I feel anxious about work", user_id=uuid.uuid4(), days_ago=3),
            _make_memory("I'm content overall", user_id=uuid.uuid4(), days_ago=5),
        ]
        output = await agent.execute({
            "user_id": str(uuid.uuid4()),
            "semantic_memories": [
                {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
                for m in memories
            ],
        })
        assert output.status == "success"
        spots = output.data.get("blind_spots", [])
        assert len(spots) >= 1


# ---------------------------------------------------------------------------
# Validation failures
# ---------------------------------------------------------------------------

class TestValidationFailures:
    @pytest.mark.asyncio
    async def test_no_user_id(self, agent: BlindSpotAgent) -> None:
        output = await agent.execute({})
        assert output.status == "failed"

    @pytest.mark.asyncio
    async def test_empty_llm_json(self) -> None:
        agent = BlindSpotAgent(llm=FakeLLMGateway(response="[]"), prompt_builder=FakePromptBuilder(), repo=FakeBlindSpotRepo())
        memories = [_make_memory("I feel happy", uuid.uuid4(), days_ago=1)] * 3
        output = await agent.execute({
            "user_id": str(uuid.uuid4()),
            "semantic_memories": [
                {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
                for m in memories
            ],
        })
        assert output.status == "success"


# ---------------------------------------------------------------------------
# Scheduled vs on-demand
# ---------------------------------------------------------------------------

class TestExecutionModes:
    @pytest.mark.asyncio
    async def test_on_demand(self, agent: BlindSpotAgent, uid: uuid.UUID) -> None:
        memories = [_make_memory("I feel happy", uid, days_ago=1)] * 3
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
    async def test_scheduled(self, agent: BlindSpotAgent, uid: uuid.UUID) -> None:
        memories = [_make_memory("I feel happy", uid, days_ago=1)] * 3
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
    async def test_events_emitted(self, agent: BlindSpotAgent, uid: uuid.UUID) -> None:
        memories = [
            _make_memory("I feel happy", uid, days_ago=1),
            _make_memory("I feel anxious", uid, days_ago=3),
            _make_memory("I'm content", uid, days_ago=5),
        ]
        output = await agent.execute({
            "user_id": str(uid),
            "semantic_memories": [
                {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
                for m in memories
            ],
        })
        assert len(output.events) >= 1

    @pytest.mark.asyncio
    async def test_metadata_complete(self, agent: BlindSpotAgent, uid: uuid.UUID) -> None:
        memories = [
            _make_memory("I feel happy", uid, days_ago=1),
            _make_memory("I feel anxious", uid, days_ago=3),
            _make_memory("I'm content", uid, days_ago=5),
        ]
        output = await agent.execute({
            "user_id": str(uid),
            "semantic_memories": [
                {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
                for m in memories
            ],
        })
        assert "evidence_analyzed" in output.metadata
        assert "latency_ms" in output.metadata

    @pytest.mark.asyncio
    async def test_no_repo_still_works(self) -> None:
        agent = BlindSpotAgent(llm=FakeLLMGateway(), prompt_builder=FakePromptBuilder(), repo=None)
        memories = [_make_memory("I feel happy", user_id=uuid.uuid4(), days_ago=1)] * 3
        output = await agent.execute({
            "user_id": str(uuid.uuid4()),
            "semantic_memories": [
                {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
                for m in memories
            ],
        })
        assert output.status == "success"

    @pytest.mark.asyncio
    async def test_with_patterns(self, agent: BlindSpotAgent, uid: uuid.UUID) -> None:
        memories = [_make_memory("I avoid things", uid, days_ago=10)] * 3
        patterns = [{"name": "avoidance_pattern", "description": "tends to avoid"}]
        output = await agent.execute({
            "user_id": str(uid),
            "semantic_memories": [
                {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
                for m in memories
            ],
            "patterns": patterns,
        })
        assert output.status == "success"

    @pytest.mark.asyncio
    async def test_with_reflections(self, agent: BlindSpotAgent, uid: uuid.UUID) -> None:
        memories = [_make_memory("I feel happy", uid, days_ago=1)] * 3
        reflections = [{"summary": "User shows growth in self-awareness"}]
        output = await agent.execute({
            "user_id": str(uid),
            "semantic_memories": [
                {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
                for m in memories
            ],
            "reflections": reflections,
        })
        assert output.status == "success"

    @pytest.mark.asyncio
    async def test_max_blind_spots_respected(self) -> None:
        config = BlindSpotConfig(max_blind_spots_per_run=2)
        agent = BlindSpotAgent(llm=FakeLLMGateway(), prompt_builder=FakePromptBuilder(), repo=FakeBlindSpotRepo(), config=config)
        uid = uuid.uuid4()
        memories = [
            _make_memory("I feel happy", uid, days_ago=1),
            _make_memory("I feel anxious", uid, days_ago=2),
            _make_memory("I feel sad", uid, days_ago=3),
            _make_memory("I feel angry", uid, days_ago=4),
            _make_memory("I feel scared", uid, days_ago=5),
        ]
        output = await agent.execute({
            "user_id": str(uid),
            "semantic_memories": [
                {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
                for m in memories
            ],
        })
        spots = output.data.get("blind_spots", [])
        assert len(spots) <= 2


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

class TestDataclasses:
    def test_config_defaults(self) -> None:
        c = BlindSpotConfig()
        assert c.min_evidence == 2
        assert c.min_confidence == 0.3
        assert c.max_blind_spots_per_run == 10

    def test_output_defaults(self) -> None:
        bs = BlindSpotOutput()
        assert bs.title == ""
        assert bs.confidence == 0.5
        assert bs.severity == "low"
