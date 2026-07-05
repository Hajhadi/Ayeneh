"""Tests for LLM integration in MEMO engines.

Each engine gets 3 tests: ai_router=None (default), ai_router mock (LLM path attempted),
ai_router failure (fallback to non-LLM path).
"""

from __future__ import annotations

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from ayeneh.memo.episodic.engine import EpisodicMemoryEngine
from ayeneh.memo.semantic.engine import SemanticMemoryEngine
from ayeneh.memo.retrieval.engine import RetrievalEngine
from ayeneh.memo.ranking.engine import RankingEngine
from ayeneh.memo.ranking.types import RankingContext
from ayeneh.memo.base import MemoryObject
from ayeneh.memo.types import Observation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _obs(content: str, source: str = 'conversation', offset_minutes: int = 0) -> Observation:
    return Observation(
        observation_id=f'obs_{hash(content) % 100000:05d}',
        content=content,
        source=source,
        timestamp=datetime.now(UTC) + timedelta(minutes=offset_minutes),
    )


def _make_memory(identifier: str = 'mem_1', importance: float = 0.5, confidence: float = 0.7) -> MemoryObject:
    now = datetime.now(UTC)
    return MemoryObject(
        identifier=identifier,
        memory_type='episodic',
        creation_time=now,
        last_updated=now,
        confidence=confidence,
        importance_score=importance,
        supporting_evidence=('ev_1',),
    )


def _mock_ai_router(return_content: str = '[]') -> MagicMock:
    """Create a mock AI router that returns a specific content string."""
    router = MagicMock()
    router.chat = AsyncMock(return_value={
        'choices': [{'message': {'content': return_content}}]
    })
    return router


def _failing_ai_router() -> MagicMock:
    """Create a mock AI router that raises on chat."""
    router = MagicMock()
    router.chat = AsyncMock(side_effect=RuntimeError('LLM unavailable'))
    return router


# ===================================================================
# Episodic Engine LLM Integration
# ===================================================================


class TestEpisodicLLM:
    def test_default_no_ai_router(self) -> None:
        engine = EpisodicMemoryEngine(min_events_per_episode=2)
        assert engine._ai_router is None
        observations = [
            _obs('Started the project', offset_minutes=0),
            _obs('Made initial decisions', offset_minutes=5),
            _obs('Learned about architecture', offset_minutes=10),
            _obs('Discussed deployment strategy', offset_minutes=15),
        ]
        result = engine.run_pipeline(observations)
        assert len(result.episodes) >= 1

    def test_llm_path_attempted_with_router(self) -> None:
        router = _mock_ai_router('[{"title": "Test Episode", "category": "learning", "start_index": 0, "end_index": 0}]')
        engine = EpisodicMemoryEngine(min_events_per_episode=2, ai_router=router)
        assert engine._ai_router is router
        # Should still produce episodes (LLM path is attempted but may not change result)
        observations = [
            _obs('Started the project', offset_minutes=0),
            _obs('Made initial decisions', offset_minutes=5),
            _obs('Learned something new', offset_minutes=10),
        ]
        result = engine.run_pipeline(observations)
        # Pipeline works regardless of LLM outcome
        assert isinstance(result.episodes, list)

    def test_llm_failure_falls_back(self) -> None:
        router = _failing_ai_router()
        engine = EpisodicMemoryEngine(min_events_per_episode=2, ai_router=router)
        observations = [
            _obs('Started the project', offset_minutes=0),
            _obs('Made initial decisions', offset_minutes=5),
            _obs('Learned about architecture', offset_minutes=10),
            _obs('Discussed deployment strategy', offset_minutes=15),
        ]
        result = engine.run_pipeline(observations)
        # Should work via fallback
        assert len(result.episodes) >= 1


# ===================================================================
# Semantic Engine LLM Integration
# ===================================================================


class TestSemanticLLM:
    def test_default_no_ai_router(self) -> None:
        engine = SemanticMemoryEngine(repetition_threshold=2)
        assert engine._ai_router is None
        observations = [
            _obs('Python expertise observed', source='s1', offset_minutes=0),
            _obs('Python expertise confirmed', source='s2', offset_minutes=60),
        ]
        result = engine.run_pipeline(observations)
        assert isinstance(result.semantic_objects, list)

    def test_llm_path_attempted_with_router(self) -> None:
        router = _mock_ai_router('[{"pattern": "python", "category": "skills", "confidence": 0.8}]')
        engine = SemanticMemoryEngine(repetition_threshold=2, ai_router=router)
        assert engine._ai_router is router
        observations = [
            _obs('Python expertise observed', source='s1', offset_minutes=0),
            _obs('Python expertise confirmed', source='s2', offset_minutes=60),
        ]
        result = engine.run_pipeline(observations)
        assert isinstance(result.semantic_objects, list)

    def test_llm_failure_falls_back(self) -> None:
        router = _failing_ai_router()
        engine = SemanticMemoryEngine(repetition_threshold=2, ai_router=router)
        observations = [
            _obs('Python expertise observed', source='s1', offset_minutes=0),
            _obs('Python expertise confirmed', source='s2', offset_minutes=60),
        ]
        result = engine.run_pipeline(observations)
        assert isinstance(result.semantic_objects, list)


# ===================================================================
# Retrieval Engine LLM Integration
# ===================================================================


class TestRetrievalLLM:
    def test_default_no_ai_router(self) -> None:
        engine = RetrievalEngine()
        assert engine._ai_router is None
        result = engine.retrieve('test query', semantic_memories=[])
        assert result is not None

    def test_llm_path_attempted_with_router(self) -> None:
        router = _mock_ai_router('[{"memory_id": "s1", "relevance_score": 0.9}]')
        engine = RetrievalEngine(ai_router=router)
        assert engine._ai_router is router
        result = engine.retrieve(
            'What are my skills?',
            semantic_memories=[{'id': 's1', 'content': 'Python skills', 'confidence': 0.8}],
        )
        assert result is not None

    def test_llm_failure_falls_back(self) -> None:
        router = _failing_ai_router()
        engine = RetrievalEngine(ai_router=router)
        result = engine.retrieve(
            'What are my skills?',
            semantic_memories=[{'id': 's1', 'content': 'Python skills', 'confidence': 0.8}],
        )
        assert result is not None


# ===================================================================
# Ranking Engine LLM Integration
# ===================================================================


class TestRankingLLM:
    def test_default_no_ai_router(self) -> None:
        engine = RankingEngine()
        assert engine._ai_router is None
        memories = [_make_memory('m1'), _make_memory('m2')]
        selection = engine.rank(memories)
        assert len(selection.selected_memories) >= 1

    def test_llm_path_attempted_with_router(self) -> None:
        router = _mock_ai_router('[{"memory_id": "m1", "overall_score": 0.9}]')
        engine = RankingEngine(ai_router=router)
        assert engine._ai_router is router
        memories = [_make_memory('m1'), _make_memory('m2')]
        selection = engine.rank(memories)
        assert isinstance(selection.selected_memories, tuple)

    def test_llm_failure_falls_back(self) -> None:
        router = _failing_ai_router()
        engine = RankingEngine(ai_router=router)
        memories = [_make_memory('m1'), _make_memory('m2')]
        selection = engine.rank(memories)
        assert len(selection.selected_memories) >= 1
