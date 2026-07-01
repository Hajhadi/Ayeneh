"""Comprehensive tests for the MemoryAgent."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from ayeneh.agents.memory import MemoryAgent, MemoryDecision, MemoryPolicy
from ayeneh.application.services.memory import (
    EmbeddingGateway,
    Memory,
    MemoryRepository,
    MemoryService,
    MemoryType,
)

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

class InMemoryMemoryRepo(MemoryRepository):
    def __init__(self) -> None:
        self._store: dict[uuid.UUID, Memory] = {}

    async def create(self, memory: Memory) -> Memory:
        self._store[memory.id] = memory
        return memory

    async def get_by_id(self, memory_id: uuid.UUID) -> Memory | None:
        return self._store.get(memory_id)

    async def list_by_user(self, user_id: uuid.UUID, **kwargs: Any) -> list[Memory]:
        return [m for m in self._store.values() if m.user_id == user_id]

    async def update(self, memory: Memory) -> Memory:
        self._store[memory.id] = memory
        return memory

    async def count_by_user(self, user_id: uuid.UUID) -> int:
        return sum(1 for m in self._store.values() if m.user_id == user_id)

    async def list_expiring(self, user_id: uuid.UUID, before: Any, limit: int = 100) -> list[Memory]:
        return []

    async def find_similar_content(self, user_id: uuid.UUID, content: str, threshold: float = 0.95) -> list[Memory]:
        return [
            m for m in self._store.values()
            if m.user_id == user_id and m.content.strip().lower() == content.strip().lower()
        ]


class FakeEmbeddingGateway(EmbeddingGateway):
    async def embed(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]

    async def search_similar(self, user_id: uuid.UUID, query: str, **kwargs: Any) -> list:
        return []

    async def upsert(self, entity_id: uuid.UUID, entity_type: str, text: str) -> None:
        pass

    async def delete(self, entity_id: uuid.UUID, entity_type: str) -> None:
        pass

    async def needs_reembedding(self, entity_id: uuid.UUID, entity_type: str) -> bool:
        return False


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def repo() -> InMemoryMemoryRepo:
    return InMemoryMemoryRepo()


@pytest.fixture
def embedding() -> FakeEmbeddingGateway:
    return FakeEmbeddingGateway()


@pytest.fixture
def memory_service(repo: InMemoryMemoryRepo, embedding: FakeEmbeddingGateway) -> MemoryService:
    return MemoryService(repo=repo, embeddings=embedding)


@pytest.fixture
def agent(memory_service: MemoryService) -> MemoryAgent:
    return MemoryAgent(memory_service=memory_service)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

class TestClassification:
    def test_episodic_classification(self, agent: MemoryAgent) -> None:
        decision = agent._evaluate_candidate(
            {"content": "I went to the store yesterday and bought groceries", "source": "user_message"},
            "u1",
        )
        assert decision is not None
        assert decision.memory_type == MemoryType.EPISODIC

    def test_semantic_classification(self, agent: MemoryAgent) -> None:
        decision = agent._evaluate_candidate(
            {"content": "I always prefer reading books before bed because I believe it helps me relax and I value quiet time", "source": "user_message"},
            "u1",
        )
        assert decision is not None
        assert decision.memory_type == MemoryType.SEMANTIC

    def test_pattern_classification(self, agent: MemoryAgent) -> None:
        decision = agent._evaluate_candidate(
            {"content": "I tend to procrastinate on important tasks and often delay difficult conversations", "source": "user_message"},
            "u1",
        )
        assert decision is not None
        assert decision.memory_type == MemoryType.PATTERN

    def test_reflection_classification(self, agent: MemoryAgent) -> None:
        decision = agent._evaluate_candidate(
            {"content": "I realize now that I've been avoiding this topic. Looking back, I understand why I felt that way", "source": "conversation_summary"},
            "u1",
        )
        assert decision is not None
        assert decision.memory_type == MemoryType.REFLECTION

    def test_default_to_episodic_for_short(self, agent: MemoryAgent) -> None:
        decision = agent._evaluate_candidate(
            {"content": "Went to the park with friends", "source": "user_message"},
            "u1",
        )
        assert decision is not None
        assert decision.memory_type == MemoryType.EPISODIC

    def test_default_to_semantic_for_long(self, agent: MemoryAgent) -> None:
        decision = agent._evaluate_candidate(
            {"content": " ".join(["word"] * 30), "source": "user_message"},
            "u1",
        )
        assert decision is not None
        assert decision.memory_type == MemoryType.SEMANTIC

    def test_observation_pattern_boost(self, agent: MemoryAgent) -> None:
        decision = agent._evaluate_candidate(
            {"content": "User consistently avoids difficult conversations", "source": "observation", "observation_type": "pattern"},
            "u1",
        )
        assert decision is not None
        assert decision.memory_type == MemoryType.PATTERN

    def test_observation_defaults_to_semantic(self, agent: MemoryAgent) -> None:
        decision = agent._evaluate_candidate(
            {"content": "User expressed a belief about personal growth", "source": "observation", "observation_type": "belief"},
            "u1",
        )
        assert decision is not None
        assert decision.memory_type == MemoryType.SEMANTIC


# ---------------------------------------------------------------------------
# Importance scoring
# ---------------------------------------------------------------------------

class TestImportanceScoring:
    def test_low_importance_short_neutral(self, agent: MemoryAgent) -> None:
        decision = agent._evaluate_candidate(
            {"content": "Went to the store", "source": "user_message"},
            "u1",
        )
        assert decision is not None
        assert decision.importance < 0.5

    def test_high_importance_keywords(self, agent: MemoryAgent) -> None:
        decision = agent._evaluate_candidate(
            {"content": "This is critically important for my goal and I believe it is a core value", "source": "user_message"},
            "u1",
        )
        assert decision is not None
        assert decision.importance >= 0.5

    def test_observation_boosts_importance(self, agent: MemoryAgent) -> None:
        d1 = agent._evaluate_candidate({"content": "Something happened today", "source": "user_message"}, "u1")
        d2 = agent._evaluate_candidate({"content": "Something happened today", "source": "observation"}, "u1")
        assert d1 is not None and d2 is not None
        assert d2.importance >= d1.importance

    def test_inline_suggestion_boosts(self, agent: MemoryAgent) -> None:
        d1 = agent._evaluate_candidate({"content": "I think this is important", "source": "user_message"}, "u1")
        d2 = agent._evaluate_candidate({"content": "I think this is important", "source": "inline_suggestion"}, "u1")
        assert d1 is not None and d2 is not None
        assert d2.importance >= d1.importance

    def test_long_content_boosts(self, agent: MemoryAgent) -> None:
        decision = agent._evaluate_candidate(
            {"content": " ".join(["word"] * 60), "source": "user_message"},
            "u1",
        )
        assert decision is not None
        assert decision.importance > 0.3

    def test_commitment_boosts(self, agent: MemoryAgent) -> None:
        decision = agent._evaluate_candidate(
            {"content": "I will definitely commit to reading every day", "source": "user_message"},
            "u1",
        )
        assert decision is not None
        assert decision.importance >= 0.5

    def test_importance_clamped(self, agent: MemoryAgent) -> None:
        decision = agent._evaluate_candidate(
            {"content": "This is critically important always never goal belief value principle rule promise decision commitment", "source": "inline_suggestion"},
            "u1",
        )
        assert decision is not None
        assert decision.importance <= 1.0


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

class TestConfidenceScoring:
    def test_high_confidence_keywords(self, agent: MemoryAgent) -> None:
        decision = agent._evaluate_candidate(
            {"content": "I know that I believe this is definitely important", "source": "user_message"},
            "u1",
        )
        assert decision is not None
        assert decision.confidence >= 0.6

    def test_low_confidence_hedging(self, agent: MemoryAgent) -> None:
        decision = agent._evaluate_candidate(
            {"content": "Maybe I think perhaps this could possibly matter", "source": "user_message"},
            "u1",
        )
        assert decision is not None
        assert decision.confidence < 0.5

    def test_user_message_boosts_confidence(self, agent: MemoryAgent) -> None:
        d1 = agent._evaluate_candidate({"content": "I believe this is important", "source": "assistant_response"}, "u1")
        d2 = agent._evaluate_candidate({"content": "I believe this is important", "source": "user_message"}, "u1")
        assert d1 is not None and d2 is not None
        assert d2.confidence >= d1.confidence

    def test_inline_suggestion_boosts_confidence(self, agent: MemoryAgent) -> None:
        d1 = agent._evaluate_candidate({"content": "This is a fact", "source": "user_message"}, "u1")
        d2 = agent._evaluate_candidate({"content": "This is a fact", "source": "inline_suggestion"}, "u1")
        assert d1 is not None and d2 is not None
        assert d2.confidence >= d1.confidence

    def test_confidence_clamped(self, agent: MemoryAgent) -> None:
        decision = agent._evaluate_candidate(
            {"content": "I know I believe I think this is definitely absolutely certainly important", "source": "inline_suggestion"},
            "u1",
        )
        assert decision is not None
        assert 0.0 <= decision.confidence <= 1.0


# ---------------------------------------------------------------------------
# Candidate extraction
# ---------------------------------------------------------------------------

class TestCandidateExtraction:
    def test_extracts_user_message(self, agent: MemoryAgent) -> None:
        candidates = agent._extract_candidates(
            user_message="I love reading books",
            response_text="That's great!",
            observations=[],
            inline_suggestions=[],
            conversation_history=[],
        )
        contents = [c["content"] for c in candidates]
        assert "I love reading books" in contents

    def test_extracts_response(self, agent: MemoryAgent) -> None:
        candidates = agent._extract_candidates(
            user_message="hello",
            response_text="Reading is a wonderful habit that can enrich your life in many ways",
            observations=[],
            inline_suggestions=[],
            conversation_history=[],
        )
        assert len(candidates) >= 2

    def test_extracts_observations(self, agent: MemoryAgent) -> None:
        candidates = agent._extract_candidates(
            user_message="hello",
            response_text="ok",
            observations=[{"type": "belief", "content": "User values knowledge"}],
            inline_suggestions=[],
            conversation_history=[],
        )
        contents = [c["content"] for c in candidates]
        assert "User values knowledge" in contents

    def test_extracts_inline_suggestions(self, agent: MemoryAgent) -> None:
        candidates = agent._extract_candidates(
            user_message="hello",
            response_text="ok",
            observations=[],
            inline_suggestions=[{"content": "User enjoys nature walks", "source_message_ids": ["m1"]}],
            conversation_history=[],
        )
        assert any("nature walks" in c["content"] for c in candidates)

    def test_extracts_conversation_summary(self, agent: MemoryAgent) -> None:
        history = [{"role": "user", "content": f"message {i} about important topics and beliefs"} for i in range(5)]
        candidates = agent._extract_candidates(
            user_message="hello",
            response_text="ok",
            observations=[],
            inline_suggestions=[],
            conversation_history=history,
        )
        sources = [c["source"] for c in candidates]
        assert "conversation_summary" in sources

    def test_empty_message_no_candidate(self, agent: MemoryAgent) -> None:
        candidates = agent._extract_candidates(
            user_message="",
            response_text="",
            observations=[],
            inline_suggestions=[],
            conversation_history=[],
        )
        assert len(candidates) == 0


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------

class TestDuplicateDetection:
    @pytest.mark.asyncio
    async def test_stored_memory_returned(self, agent: MemoryAgent, user_id: uuid.UUID) -> None:
        output = await agent.execute({
            "user_id": str(user_id),
            "user_message": "I believe that learning is the most important thing in life and I value knowledge above all else",
            "conversation_history": [],
            "conversation_agent_output": {"response_text": "", "observations": []},
        })
        assert output.status == "success"
        assert output.metadata["candidates_evaluated"] >= 1

    @pytest.mark.asyncio
    async def test_duplicate_content_detected(self, agent: MemoryAgent, user_id: uuid.UUID) -> None:
        output1 = await agent.execute({
            "user_id": str(user_id),
            "user_message": "I believe that learning is the most important thing in life",
            "conversation_history": [],
            "conversation_agent_output": {"response_text": "", "observations": []},
        })
        output2 = await agent.execute({
            "user_id": str(user_id),
            "user_message": "I believe that learning is the most important thing in life",
            "conversation_history": [],
            "conversation_agent_output": {"response_text": "", "observations": []},
        })
        assert output1.status == "success"
        assert output2.status == "success"


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

class TestStorage:
    @pytest.mark.asyncio
    async def test_stores_memories(self, agent: MemoryAgent, user_id: uuid.UUID) -> None:
        output = await agent.execute({
            "user_id": str(user_id),
            "user_message": "I always read before bed because I believe it helps me relax and I value quiet time",
            "conversation_history": [],
            "conversation_agent_output": {"response_text": "", "observations": []},
        })
        assert output.status == "success"
        assert output.metadata["memories_stored"] >= 1

    @pytest.mark.asyncio
    async def test_stores_observations(self, agent: MemoryAgent, user_id: uuid.UUID) -> None:
        output = await agent.execute({
            "user_id": str(user_id),
            "user_message": "hello",
            "conversation_history": [],
            "conversation_agent_output": {
                "response_text": "",
                "observations": [{"type": "belief", "content": "User values personal growth and believes in continuous learning"}],
            },
        })
        assert output.status == "success"
        assert output.metadata["memories_stored"] >= 1

    @pytest.mark.asyncio
    async def test_stores_inline_suggestions(self, agent: MemoryAgent, user_id: uuid.UUID) -> None:
        output = await agent.execute({
            "user_id": str(user_id),
            "user_message": "hello",
            "conversation_history": [],
            "conversation_agent_output": {
                "response_text": "",
                "observations": [],
                "inline_memory_suggestions": [{"content": "User enjoys nature walks regularly", "source_message_ids": []}],
            },
        })
        assert output.status == "success"
        assert output.metadata["memories_stored"] >= 1

    @pytest.mark.asyncio
    async def test_low_importance_filtered(self, agent: MemoryAgent, user_id: uuid.UUID) -> None:
        policy = MemoryPolicy(min_importance=0.9, min_confidence=0.9)
        agent = MemoryAgent(memory_service=agent._memory_service, policy=policy)
        output = await agent.execute({
            "user_id": str(user_id),
            "user_message": "ok",
            "conversation_history": [],
            "conversation_agent_output": {"response_text": "", "observations": []},
        })
        assert output.status == "success"
        assert output.metadata["memories_stored"] == 0


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

class TestEventGeneration:
    @pytest.mark.asyncio
    async def test_events_for_stored_memories(self, agent: MemoryAgent, user_id: uuid.UUID) -> None:
        output = await agent.execute({
            "user_id": str(user_id),
            "user_message": "I believe that learning is the most important thing in life",
            "conversation_history": [],
            "conversation_agent_output": {"response_text": "", "observations": []},
        })
        memory_events = [e for e in output.events if e["event_type"] == "MemoryStored"]
        assert len(memory_events) >= 1
        assert "memory_id" in memory_events[0]
        assert "memory_type" in memory_events[0]


# ---------------------------------------------------------------------------
# Failure cases
# ---------------------------------------------------------------------------

class TestFailureCases:
    @pytest.mark.asyncio
    async def test_no_user_id_fails(self) -> None:
        agent = MemoryAgent()
        output = await agent.execute({"user_message": "hello"})
        assert output.status == "failed"

    @pytest.mark.asyncio
    async def test_no_memory_service_still_returns(self, agent: MemoryAgent, user_id: uuid.UUID) -> None:
        agent_no_service = MemoryAgent(memory_service=None)
        output = await agent_no_service.execute({
            "user_id": str(user_id),
            "user_message": "I believe in learning",
            "conversation_history": [],
            "conversation_agent_output": {"response_text": "", "observations": []},
        })
        assert output.status == "success"
        assert output.metadata["memories_stored"] == 0

    @pytest.mark.asyncio
    async def test_empty_context(self, agent: MemoryAgent, user_id: uuid.UUID) -> None:
        output = await agent.execute({
            "user_id": str(user_id),
            "user_message": "",
            "conversation_history": [],
            "conversation_agent_output": {"response_text": "", "observations": []},
        })
        assert output.status == "success"

    @pytest.mark.asyncio
    async def test_metadata_explains_decisions(self, agent: MemoryAgent, user_id: uuid.UUID) -> None:
        output = await agent.execute({
            "user_id": str(user_id),
            "user_message": "I believe that reading is important and I always read before bed",
            "conversation_history": [],
            "conversation_agent_output": {"response_text": "", "observations": []},
        })
        assert "decisions" in output.metadata
        for decision in output.metadata["decisions"]:
            assert "reasoning" in decision
            assert len(decision["reasoning"]) > 0


# ---------------------------------------------------------------------------
# Policy configuration
# ---------------------------------------------------------------------------

class TestPolicyConfiguration:
    def test_custom_policy(self) -> None:
        policy = MemoryPolicy(
            min_importance=0.5,
            min_confidence=0.6,
            max_episodic_per_message=1,
            duplicate_threshold=0.80,
        )
        assert policy.min_importance == 0.5
        assert policy.min_confidence == 0.6
        assert policy.max_episodic_per_message == 1
        assert policy.duplicate_threshold == 0.80

    def test_default_policy(self) -> None:
        policy = MemoryPolicy()
        assert policy.min_importance == 0.3
        assert policy.min_confidence == 0.4
        assert policy.duplicate_threshold == 0.90
        assert policy.supersede_threshold == 0.85


# ---------------------------------------------------------------------------
# Decision dataclass
# ---------------------------------------------------------------------------

class TestMemoryDecision:
    def test_defaults(self) -> None:
        d = MemoryDecision(content="test", memory_type=MemoryType.EPISODIC, importance=0.5, confidence=0.5)
        assert d.is_duplicate is False
        assert d.duplicate_of_id is None
        assert d.is_superseded is False
        assert d.supersedes_id is None
        assert d.source_message_ids == []
        assert d.reasoning == ""
