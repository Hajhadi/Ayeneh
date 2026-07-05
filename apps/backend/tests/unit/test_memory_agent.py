"""Comprehensive tests for the MemoryAgent (MEMO engines)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from ayeneh.agents.memory import MemoryAgent, MemoryPolicy


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

class FakeMEMRepository:
    """In-memory MEMRepository substitute for testing."""

    def __init__(self) -> None:
        self.episodes: list[dict[str, Any]] = []
        self.semantics: list[dict[str, Any]] = []

    async def save_episode(self, user_id: str, episode: dict[str, Any]) -> str:
        episode["id"] = str(uuid.uuid4())
        self.episodes.append(episode)
        return episode["id"]

    async def save_semantic(self, user_id: str, semantic: dict[str, Any]) -> str:
        semantic["id"] = str(uuid.uuid4())
        self.semantics.append(semantic)
        return semantic["id"]


class _FakePipelineResult:
    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


class FakeEpisodicEngine:
    def __init__(self) -> None:
        self.calls: list[list[Any]] = []

    def run_pipeline(self, observations: list[Any]) -> Any:
        self.calls.append(observations)
        return _FakePipelineResult(
            episodes=[], milestones=[], boundaries=[], emotional_landscapes={}, metadata={},
        )


class FakeSemanticEngine:
    def __init__(self) -> None:
        self.calls: list[tuple[list[Any], Any, Any]] = []

    def run_pipeline(self, observations: list[Any], *, episode_ids: Any = (), conversation_ids: Any = ()) -> Any:
        self.calls.append((observations, episode_ids, conversation_ids))
        return _FakePipelineResult(
            semantic_objects=[], knowledge_nodes=[], knowledge_edges=[], metadata={},
        )


class FakeWorkingEngine:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any, Any, Any]] = []

    def run_pipeline(self, user_input: str, *, intent: str = "recall", cognitive_focus: str = "", retrieved_memories: Any = None, recent_conversation: Any = None) -> Any:
        self.calls.append((user_input, intent, cognitive_focus, retrieved_memories))
        return _FakePipelineResult(
            activated_objects=[], deactivated_objects=[], context_switches=[],
            open_loops=[], snapshot=None, metadata={},
        )


class FakeConsolidationEngine:
    def __init__(self) -> None:
        self.calls: list[tuple[list[Any], Any]] = []

    def run_pipeline(self, working_memory_items: list[Any], *, episodes: Any = None, conversations: Any = None) -> Any:
        self.calls.append((working_memory_items, episodes))
        return _FakePipelineResult(
            processed_count=0, promoted_count=0, rejected_count=0, deferred_count=0,
            consolidated_objects=(), affected_cognitive_objects=(),
        )


class FakeRetrievalEngine:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, Any, Any]] = []

    def run_pipeline(self, request: Any, *, semantic_memories: Any = None, episodic_memories: Any = None, knowledge_graph: Any = None) -> Any:
        self.calls.append((request, semantic_memories, episodic_memories))
        return _FakePipelineResult(result=None, metadata={})


class FakeRankingEngine:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, Any]] = []

    def rank(self, memories: list[Any], context: Any = None) -> Any:
        self.calls.append((memories, context))
        return _FakePipelineResult(
            selected_memories=(), rankings=(), selection_reasoning="",
            capacity_used=0, capacity_max=20,
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def fake_repo() -> FakeMEMRepository:
    return FakeMEMRepository()


@pytest.fixture
def agent(fake_repo: FakeMEMRepository) -> MemoryAgent:
    a = MemoryAgent(repository=fake_repo)
    # Inject fakes to avoid heavy init
    a._episodic_engine = FakeEpisodicEngine()
    a._semantic_engine = FakeSemanticEngine()
    a._working_engine = FakeWorkingEngine()
    a._consolidation_engine = FakeConsolidationEngine()
    a._retrieval_engine = FakeRetrievalEngine()
    a._ranking_engine = FakeRankingEngine()
    return a


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

class TestClassification:
    def test_episodic_classification(self, agent: MemoryAgent) -> None:
        d = agent._evaluate_candidate(
            {"content": "I went to the store yesterday and bought groceries", "source": "user_message"},
            "u1",
        )
        assert d is not None
        assert d["memory_type"] == "episodic"

    def test_semantic_classification(self, agent: MemoryAgent) -> None:
        d = agent._evaluate_candidate(
            {"content": "I always prefer reading books before bed because I believe it helps me relax and I value quiet time", "source": "user_message"},
            "u1",
        )
        assert d is not None
        assert d["memory_type"] == "semantic"

    def test_pattern_classification(self, agent: MemoryAgent) -> None:
        d = agent._evaluate_candidate(
            {"content": "I tend to procrastinate on important tasks and often delay difficult conversations", "source": "user_message"},
            "u1",
        )
        assert d is not None
        assert d["memory_type"] == "pattern"

    def test_reflection_classification(self, agent: MemoryAgent) -> None:
        d = agent._evaluate_candidate(
            {"content": "I realize now that I've been avoiding this topic. Looking back, I understand why I felt that way", "source": "conversation_summary"},
            "u1",
        )
        assert d is not None
        assert d["memory_type"] == "reflection"

    def test_default_to_episodic_for_short(self, agent: MemoryAgent) -> None:
        d = agent._evaluate_candidate(
            {"content": "Went to the park with friends", "source": "user_message"},
            "u1",
        )
        assert d is not None
        assert d["memory_type"] == "episodic"

    def test_default_to_semantic_for_long(self, agent: MemoryAgent) -> None:
        d = agent._evaluate_candidate(
            {"content": " ".join(["word"] * 30), "source": "user_message"},
            "u1",
        )
        assert d is not None
        assert d["memory_type"] == "semantic"

    def test_observation_pattern_boost(self, agent: MemoryAgent) -> None:
        d = agent._evaluate_candidate(
            {"content": "User consistently avoids difficult conversations", "source": "observation"},
            "u1",
        )
        assert d is not None
        assert d["memory_type"] == "pattern"

    def test_observation_defaults_to_semantic(self, agent: MemoryAgent) -> None:
        d = agent._evaluate_candidate(
            {"content": "User expressed a belief about personal growth", "source": "observation"},
            "u1",
        )
        assert d is not None
        assert d["memory_type"] == "semantic"


# ---------------------------------------------------------------------------
# Importance scoring
# ---------------------------------------------------------------------------

class TestImportanceScoring:
    def test_low_importance_short_neutral(self, agent: MemoryAgent) -> None:
        d = agent._evaluate_candidate(
            {"content": "Went to the store", "source": "user_message"},
            "u1",
        )
        assert d is not None
        assert d["importance"] < 0.5

    def test_high_importance_keywords(self, agent: MemoryAgent) -> None:
        d = agent._evaluate_candidate(
            {"content": "This is critically important for my goal and I believe it is a core value", "source": "user_message"},
            "u1",
        )
        assert d is not None
        assert d["importance"] >= 0.5

    def test_observation_boosts_importance(self, agent: MemoryAgent) -> None:
        d1 = agent._evaluate_candidate({"content": "Something happened today", "source": "user_message"}, "u1")
        d2 = agent._evaluate_candidate({"content": "Something happened today", "source": "observation"}, "u1")
        assert d1 is not None and d2 is not None
        assert d2["importance"] >= d1["importance"]

    def test_inline_suggestion_boosts(self, agent: MemoryAgent) -> None:
        d1 = agent._evaluate_candidate({"content": "I think this is important", "source": "user_message"}, "u1")
        d2 = agent._evaluate_candidate({"content": "I think this is important", "source": "inline_suggestion"}, "u1")
        assert d1 is not None and d2 is not None
        assert d2["importance"] >= d1["importance"]

    def test_long_content_boosts(self, agent: MemoryAgent) -> None:
        d = agent._evaluate_candidate(
            {"content": " ".join(["word"] * 60), "source": "user_message"},
            "u1",
        )
        assert d is not None
        assert d["importance"] > 0.3

    def test_commitment_boosts(self, agent: MemoryAgent) -> None:
        d = agent._evaluate_candidate(
            {"content": "I will definitely commit to reading every day", "source": "user_message"},
            "u1",
        )
        assert d is not None
        assert d["importance"] >= 0.5

    def test_importance_clamped(self, agent: MemoryAgent) -> None:
        d = agent._evaluate_candidate(
            {"content": "This is critically important always never goal belief value principle rule promise decision commitment", "source": "inline_suggestion"},
            "u1",
        )
        assert d is not None
        assert d["importance"] <= 1.0


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

class TestConfidenceScoring:
    def test_high_confidence_keywords(self, agent: MemoryAgent) -> None:
        d = agent._evaluate_candidate(
            {"content": "I know that I believe this is definitely important", "source": "user_message"},
            "u1",
        )
        assert d is not None
        assert d["confidence"] >= 0.6

    def test_low_confidence_hedging(self, agent: MemoryAgent) -> None:
        d = agent._evaluate_candidate(
            {"content": "Maybe I think perhaps this could possibly matter", "source": "user_message"},
            "u1",
        )
        assert d is not None
        assert d["confidence"] < 0.5

    def test_user_message_boosts_confidence(self, agent: MemoryAgent) -> None:
        d1 = agent._evaluate_candidate({"content": "I believe this is important", "source": "assistant_response"}, "u1")
        d2 = agent._evaluate_candidate({"content": "I believe this is important", "source": "user_message"}, "u1")
        assert d1 is not None and d2 is not None
        assert d2["confidence"] >= d1["confidence"]

    def test_inline_suggestion_boosts_confidence(self, agent: MemoryAgent) -> None:
        d1 = agent._evaluate_candidate({"content": "This is a fact", "source": "user_message"}, "u1")
        d2 = agent._evaluate_candidate({"content": "This is a fact", "source": "inline_suggestion"}, "u1")
        assert d1 is not None and d2 is not None
        assert d2["confidence"] >= d1["confidence"]

    def test_confidence_clamped(self, agent: MemoryAgent) -> None:
        d = agent._evaluate_candidate(
            {"content": "I know I believe I think this is definitely absolutely certainly important", "source": "inline_suggestion"},
            "u1",
        )
        assert d is not None
        assert 0.0 <= d["confidence"] <= 1.0


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
        assert "I love reading books" in [c["content"] for c in candidates]

    def test_extracts_response(self, agent: MemoryAgent) -> None:
        candidates = agent._extract_candidates(
            user_message="hello",
            response_text="Reading is a wonderful habit that can enrich your life in many ways",
            observations=[], inline_suggestions=[], conversation_history=[],
        )
        assert len(candidates) >= 2

    def test_extracts_observations(self, agent: MemoryAgent) -> None:
        candidates = agent._extract_candidates(
            user_message="hello", response_text="ok",
            observations=[{"type": "belief", "content": "User values knowledge"}],
            inline_suggestions=[], conversation_history=[],
        )
        assert "User values knowledge" in [c["content"] for c in candidates]

    def test_extracts_inline_suggestions(self, agent: MemoryAgent) -> None:
        candidates = agent._extract_candidates(
            user_message="hello", response_text="ok", observations=[],
            inline_suggestions=[{"content": "User enjoys nature walks", "source_message_ids": ["m1"]}],
            conversation_history=[],
        )
        assert any("nature walks" in c["content"] for c in candidates)

    def test_extracts_conversation_summary(self, agent: MemoryAgent) -> None:
        history = [{"role": "user", "content": f"message {i} about important topics and beliefs"} for i in range(5)]
        candidates = agent._extract_candidates(
            user_message="hello", response_text="ok", observations=[],
            inline_suggestions=[], conversation_history=history,
        )
        assert "conversation_summary" in [c["source"] for c in candidates]

    def test_empty_message_no_candidate(self, agent: MemoryAgent) -> None:
        candidates = agent._extract_candidates(
            user_message="", response_text="", observations=[],
            inline_suggestions=[], conversation_history=[],
        )
        assert len(candidates) == 0


# ---------------------------------------------------------------------------
# Execute integration
# ---------------------------------------------------------------------------

class TestExecute:
    @pytest.mark.asyncio
    async def test_no_user_id_fails(self, agent: MemoryAgent) -> None:
        output = await agent.execute({"user_message": "hello"})
        assert output.status == "failed"

    @pytest.mark.asyncio
    async def test_success_without_repository(self, user_id: str) -> None:
        a = MemoryAgent(repository=None)
        a._episodic_engine = FakeEpisodicEngine()
        a._semantic_engine = FakeSemanticEngine()
        a._working_engine = FakeWorkingEngine()
        a._consolidation_engine = FakeConsolidationEngine()
        a._retrieval_engine = FakeRetrievalEngine()
        a._ranking_engine = FakeRankingEngine()
        output = await a.execute({
            "user_id": user_id,
            "user_message": "I believe in learning",
            "conversation_history": [],
            "conversation_agent_output": {"response_text": "", "observations": []},
        })
        assert output.status == "success"
        assert output.metadata["memories_stored"] == 0

    @pytest.mark.asyncio
    async def test_success_with_repository(self, agent: MemoryAgent, fake_repo: FakeMEMRepository, user_id: str) -> None:
        output = await agent.execute({
            "user_id": user_id,
            "user_message": "I believe that learning is the most important thing in life",
            "conversation_history": [],
            "conversation_agent_output": {"response_text": "", "observations": []},
        })
        assert output.status == "success"
        assert "new_memories" in output.data

    @pytest.mark.asyncio
    async def test_empty_context(self, agent: MemoryAgent, user_id: str) -> None:
        output = await agent.execute({
            "user_id": user_id,
            "user_message": "",
            "conversation_history": [],
            "conversation_agent_output": {"response_text": "", "observations": []},
        })
        assert output.status == "success"

    @pytest.mark.asyncio
    async def test_metadata_explains_decisions(self, agent: MemoryAgent, user_id: str) -> None:
        output = await agent.execute({
            "user_id": user_id,
            "user_message": "I believe that reading is important and I always read before bed",
            "conversation_history": [],
            "conversation_agent_output": {"response_text": "", "observations": []},
        })
        assert "decisions" in output.metadata
        for decision in output.metadata["decisions"]:
            assert "reasoning" in decision
            assert len(decision["reasoning"]) > 0


# ---------------------------------------------------------------------------
# MEMO engine wiring
# ---------------------------------------------------------------------------

class TestMEMOWiring:
    @pytest.mark.asyncio
    async def test_episodic_engine_called(self, agent: MemoryAgent, user_id: str) -> None:
        await agent.execute({
            "user_id": user_id,
            "user_message": "I went to the store today and bought groceries for dinner",
            "conversation_history": [],
            "conversation_agent_output": {"response_text": "", "observations": []},
        })
        episodic = agent._episodic_engine
        assert len(episodic.calls) == 1
        assert len(episodic.calls[0]) > 0

    @pytest.mark.asyncio
    async def test_semantic_engine_called(self, agent: MemoryAgent, user_id: str) -> None:
        await agent.execute({
            "user_id": user_id,
            "user_message": "I always prefer reading books because I believe it helps me",
            "conversation_history": [],
            "conversation_agent_output": {"response_text": "", "observations": []},
        })
        semantic = agent._semantic_engine
        assert len(semantic.calls) == 1
        assert len(semantic.calls[0][0]) > 0

    @pytest.mark.asyncio
    async def test_repo_save_episode_called(self, agent: MemoryAgent, fake_repo: FakeMEMRepository, user_id: str) -> None:
        # Patch engines to return non-empty results
        fake_ep = _FakePipelineResult(
            episodes=[_FakePipelineResult(
                identifier="ep_test", title="Test Episode", summary="Test summary",
                category="learning", state="active", start_time=None, end_time=None,
                estimated_duration=0.0, confidence=0.8, primary_context="",
                supporting_evidence=("ev1",),
            )],
        )
        agent._episodic_engine.run_pipeline = lambda obs: fake_ep  # type: ignore[assignment]

        await agent.execute({
            "user_id": user_id,
            "user_message": "I decided to learn Python today",
            "conversation_history": [],
            "conversation_agent_output": {"response_text": "", "observations": []},
        })
        assert len(fake_repo.episodes) == 1
        assert fake_repo.episodes[0]["title"] == "Test Episode"

    @pytest.mark.asyncio
    async def test_repo_save_semantic_called(self, agent: MemoryAgent, fake_repo: FakeMEMRepository, user_id: str) -> None:
        fake_sm = _FakePipelineResult(
            semantic_objects=[_FakePipelineResult(
                identifier="sm_test", knowledge_statement="Pattern observed: test",
                knowledge_category="skills", supporting_evidence=("ev1",),
                supporting_episodes=("ep1",), confidence=0.7, importance=0.5,
                temporal_stability="long_term",
            )],
        )
        agent._semantic_engine.run_pipeline = lambda obs, **kw: fake_sm  # type: ignore[assignment]

        await agent.execute({
            "user_id": user_id,
            "user_message": "I always use Python for data analysis",
            "conversation_history": [],
            "conversation_agent_output": {"response_text": "", "observations": []},
        })
        assert len(fake_repo.semantics) == 1
        assert fake_repo.semantics[0]["knowledge_category"] == "skills"


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
# Low-importance filtering
# ---------------------------------------------------------------------------

class TestFiltering:
    @pytest.mark.asyncio
    async def test_low_importance_filtered(self, agent: MemoryAgent, user_id: str) -> None:
        policy = MemoryPolicy(min_importance=0.9, min_confidence=0.9)
        a = MemoryAgent(policy=policy, repository=agent._repo)
        a._episodic_engine = agent._episodic_engine
        a._semantic_engine = agent._semantic_engine
        a._working_engine = agent._working_engine
        a._consolidation_engine = agent._consolidation_engine
        a._retrieval_engine = agent._retrieval_engine
        a._ranking_engine = agent._ranking_engine
        output = await a.execute({
            "user_id": user_id,
            "user_message": "ok",
            "conversation_history": [],
            "conversation_agent_output": {"response_text": "", "observations": []},
        })
        assert output.status == "success"
        assert output.metadata["memories_stored"] == 0

    @pytest.mark.asyncio
    async def test_short_content_filtered(self, agent: MemoryAgent, user_id: str) -> None:
        output = await agent.execute({
            "user_id": user_id,
            "user_message": "hi",
            "conversation_history": [],
            "conversation_agent_output": {"response_text": "", "observations": []},
        })
        assert output.status == "success"
        assert output.metadata["memories_stored"] == 0
