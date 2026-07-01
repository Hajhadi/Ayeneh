"""Comprehensive tests for the PatternAgent."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from ayeneh.agents.pattern import (
    DetectedPattern,
    PatternAgent,
    PatternConfig,
    TrendDirection,
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


def _context_with_memories(memories: list[Memory], existing_patterns: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "user_id": str(memories[0].user_id) if memories else str(uuid.uuid4()),
        "semantic_memories": [
            {"id": str(m.id), "user_id": str(m.user_id), "type": m.type.value, "content": m.content, "confidence": m.confidence, "created_at": m.created_at.isoformat()}
            for m in memories
        ],
        "existing_patterns": existing_patterns or [],
    }


@pytest.fixture
def uid() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def agent() -> PatternAgent:
    return PatternAgent()


# ---------------------------------------------------------------------------
# New pattern detection
# ---------------------------------------------------------------------------

class TestNewPatternDetection:
    @pytest.mark.asyncio
    async def test_detects_avoidance_pattern(self, agent: PatternAgent, uid: uuid.UUID) -> None:
        memories = [
            _make_memory("I avoid difficult conversations at work", uid, days_ago=10),
            _make_memory("I keep avoiding the topic with my partner", uid, days_ago=5),
            _make_memory("I tend to postpone addressing issues", uid, days_ago=1),
        ]
        output = await agent.execute(_context_with_memories(memories))
        assert output.status == "success"
        all_p = output.data.get("new_patterns", []) + output.data.get("updated_patterns", [])
        names = [p["name"] for p in all_p]
        assert "avoidance_pattern" in names

    @pytest.mark.asyncio
    async def test_detects_perfectionism(self, agent: PatternAgent, uid: uuid.UUID) -> None:
        memories = [
            _make_memory("Nothing I do is ever perfect enough", uid, days_ago=10),
            _make_memory("I can't accept making mistakes at work", uid, days_ago=5),
            _make_memory("The standards I set for myself are impossible", uid, days_ago=1),
        ]
        output = await agent.execute(_context_with_memories(memories))
        assert output.status == "success"
        all_p = output.data.get("new_patterns", []) + output.data.get("updated_patterns", [])
        names = [p["name"] for p in all_p]
        assert "perfectionism_pattern" in names

    @pytest.mark.asyncio
    async def test_detects_reassurance_seeking(self, agent: PatternAgent, uid: uuid.UUID) -> None:
        memories = [
            _make_memory("Do you think I'm overreacting about this?", uid, days_ago=10),
            _make_memory("Am I okay? Is this normal?", uid, days_ago=5),
            _make_memory("Do you agree that this is a problem?", uid, days_ago=1),
        ]
        output = await agent.execute(_context_with_memories(memories))
        all_p = output.data.get("new_patterns", []) + output.data.get("updated_patterns", [])
        names = [p["name"] for p in all_p]
        assert "reassurance_seeking" in names

    @pytest.mark.asyncio
    async def test_detects_catastrophizing(self, agent: PatternAgent, uid: uuid.UUID) -> None:
        memories = [
            _make_memory("Everything will go wrong and it's a disaster", uid, days_ago=10),
            _make_memory("This is the worst case scenario and I'm ruined", uid, days_ago=5),
            _make_memory("I'll never recover from this catastrophe", uid, days_ago=1),
        ]
        output = await agent.execute(_context_with_memories(memories))
        all_p = output.data.get("new_patterns", []) + output.data.get("updated_patterns", [])
        names = [p["name"] for p in all_p]
        assert "catastrophizing_tendency" in names

    @pytest.mark.asyncio
    async def test_detects_positive_trend(self, agent: PatternAgent, uid: uuid.UUID) -> None:
        memories = [
            _make_memory("I feel grateful for the progress I've made this week and I'm proud of my growth", uid, days_ago=10),
            _make_memory("I'm proud of how I handled that situation and I feel happy about my improvement", uid, days_ago=5),
            _make_memory("I've been learning a lot and feeling hopeful and grateful for my success", uid, days_ago=1),
        ]
        output = await agent.execute(_context_with_memories(memories))
        all_p = output.data.get("new_patterns", []) + output.data.get("updated_patterns", [])
        names = [p["name"] for p in all_p]
        assert "positive_cognitive_trend" in names


# ---------------------------------------------------------------------------
# Existing pattern update
# ---------------------------------------------------------------------------

class TestExistingPatternUpdate:
    @pytest.mark.asyncio
    async def test_merges_with_existing(self, agent: PatternAgent, uid: uuid.UUID) -> None:
        memories = [
            _make_memory("I avoid confrontation always", uid, days_ago=10),
            _make_memory("I keep avoiding difficult topics", uid, days_ago=5),
        ]
        existing = [{"pattern_id": "existing-1", "name": "avoidance_pattern", "occurrence_count": 3, "supporting_memory_ids": []}]
        output = await agent.execute(_context_with_memories(memories, existing))
        updated = output.data.get("updated_patterns", [])
        new = output.data.get("new_patterns", [])
        all_patterns = updated + new
        assert any(p["pattern_id"] == "existing-1" for p in all_patterns)


# ---------------------------------------------------------------------------
# Duplicate merge
# ---------------------------------------------------------------------------

class TestDuplicateMerge:
    @pytest.mark.asyncio
    async def test_similar_patterns_merged(self, agent: PatternAgent, uid: uuid.UUID) -> None:
        memories = [
            _make_memory("I avoid hard conversations", uid, days_ago=10),
            _make_memory("I avoid tough discussions", uid, days_ago=5),
            _make_memory("I avoid challenging talks", uid, days_ago=1),
        ]
        output = await agent.execute(_context_with_memories(memories))
        all_p = output.data.get("new_patterns", []) + output.data.get("updated_patterns", [])
        category_names = [p["category"] for p in all_p]
        assert category_names.count("avoidance") <= 1


# ---------------------------------------------------------------------------
# Trend evolution
# ---------------------------------------------------------------------------

class TestTrendEvolution:
    @pytest.mark.asyncio
    async def test_increasing_trend(self, agent: PatternAgent, uid: uuid.UUID) -> None:
        memories = [
            _make_memory("I feel anxious about work", uid, days_ago=3),
            _make_memory("I feel anxious about the meeting", uid, days_ago=2),
            _make_memory("I feel anxious about tomorrow", uid, days_ago=1),
        ]
        output = await agent.execute(_context_with_memories(memories))
        all_p = output.data.get("new_patterns", []) + output.data.get("updated_patterns", [])
        trends = [p["trend"] for p in all_p]
        assert TrendDirection.INCREASING in trends or TrendDirection.EMERGING in trends

    @pytest.mark.asyncio
    async def test_stable_trend(self, agent: PatternAgent, uid: uuid.UUID) -> None:
        memories = [
            _make_memory("I enjoy reading", uid, days_ago=60),
            _make_memory("I enjoy reading books", uid, days_ago=30),
            _make_memory("I enjoy reading before bed", uid, days_ago=1),
        ]
        output = await agent.execute(_context_with_memories(memories))
        all_p = output.data.get("new_patterns", []) + output.data.get("updated_patterns", [])
        assert len(all_p) >= 1


# ---------------------------------------------------------------------------
# Evidence linking
# ---------------------------------------------------------------------------

class TestEvidenceLinking:
    @pytest.mark.asyncio
    async def test_evidence_populated(self, agent: PatternAgent, uid: uuid.UUID) -> None:
        memories = [
            _make_memory("I avoid confrontation", uid, days_ago=10),
            _make_memory("I keep avoiding hard topics", uid, days_ago=5),
        ]
        output = await agent.execute(_context_with_memories(memories))
        all_p = output.data.get("new_patterns", []) + output.data.get("updated_patterns", [])
        for p in all_p:
            assert len(p["evidence"]) >= 1
            assert "memory_id" in p["evidence"][0]
            assert len(p["supporting_memories"]) >= 1


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

class TestConfidenceScoring:
    @pytest.mark.asyncio
    async def test_higher_occurrence_higher_confidence(self, agent: PatternAgent, uid: uuid.UUID) -> None:
        memories_few = [_make_memory("I avoid conflict", uid, days_ago=10), _make_memory("I avoid arguments", uid, days_ago=5)]
        memories_many = [_make_memory("I avoid conflict", uid, days_ago=30)] + [_make_memory(f"I avoid situation {i}", uid, days_ago=i) for i in range(5)]
        output_few = await agent.execute(_context_with_memories(memories_few))
        output_many = await agent.execute(_context_with_memories(memories_many))
        all_few = output_few.data.get("new_patterns", []) + output_few.data.get("updated_patterns", [])
        all_many = output_many.data.get("new_patterns", []) + output_many.data.get("updated_patterns", [])
        if all_few and all_many:
            assert all_many[0]["confidence"] >= all_few[0]["confidence"]


# ---------------------------------------------------------------------------
# False positive prevention
# ---------------------------------------------------------------------------

class TestFalsePositivePrevention:
    @pytest.mark.asyncio
    async def test_insufficient_memories_filtered(self, agent: PatternAgent, uid: uuid.UUID) -> None:
        memories = [_make_memory("I feel okay today", uid)]
        output = await agent.execute(_context_with_memories(memories))
        all_p = output.data.get("new_patterns", []) + output.data.get("updated_patterns", [])
        assert len(all_p) == 0

    @pytest.mark.asyncio
    async def test_low_confidence_filtered(self) -> None:
        config = PatternConfig(min_confidence=0.99)
        agent = PatternAgent(config=config)
        memories = [
            _make_memory("I sometimes feel anxious", uuid.uuid4(), days_ago=30, confidence=0.1),
            _make_memory("Maybe I feel worried sometimes", uuid.uuid4(), days_ago=25, confidence=0.1),
        ]
        output = await agent.execute(_context_with_memories(memories))
        all_p = output.data.get("new_patterns", []) + output.data.get("updated_patterns", [])
        for p in all_p:
            assert p["confidence"] >= 0.99

    @pytest.mark.asyncio
    async def test_low_importance_filtered(self) -> None:
        config = PatternConfig(min_importance=0.9)
        agent = PatternAgent(config=config)
        memories = [
            _make_memory("I like coffee", uuid.uuid4(), days_ago=10, confidence=0.3),
            _make_memory("I like tea", uuid.uuid4(), days_ago=5, confidence=0.3),
            _make_memory("I like water", uuid.uuid4(), days_ago=1, confidence=0.3),
        ]
        output = await agent.execute(_context_with_memories(memories))
        all_p = output.data.get("new_patterns", []) + output.data.get("updated_patterns", [])
        for p in all_p:
            assert p["importance"] >= 0.9


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_no_memories(self, agent: PatternAgent, uid: uuid.UUID) -> None:
        output = await agent.execute({"user_id": str(uid)})
        assert output.status == "success"
        assert output.metadata["memories_analyzed"] == 0

    @pytest.mark.asyncio
    async def test_no_user_id(self, agent: PatternAgent) -> None:
        output = await agent.execute({})
        assert output.status == "failed"

    @pytest.mark.asyncio
    async def test_empty_memories(self, agent: PatternAgent, uid: uuid.UUID) -> None:
        output = await agent.execute({"user_id": str(uid), "semantic_memories": []})
        assert output.status == "success"

    @pytest.mark.asyncio
    async def test_metadata_complete(self, agent: PatternAgent, uid: uuid.UUID) -> None:
        memories = [_make_memory("I avoid things", uid, days_ago=10), _make_memory("I avoid stuff", uid, days_ago=5), _make_memory("I avoid problems", uid, days_ago=1)]
        output = await agent.execute(_context_with_memories(memories))
        assert "memories_analyzed" in output.metadata
        assert "candidates_extracted" in output.metadata
        assert "latency_ms" in output.metadata

    @pytest.mark.asyncio
    async def test_events_emitted(self, agent: PatternAgent, uid: uuid.UUID) -> None:
        memories = [_make_memory("I avoid conflict", uid, days_ago=10), _make_memory("I avoid arguments", uid, days_ago=5), _make_memory("I avoid hard things", uid, days_ago=1)]
        output = await agent.execute(_context_with_memories(memories))
        pattern_events = [e for e in output.events if e["event_type"] == "PatternDetected"]
        assert len(pattern_events) >= 1

    @pytest.mark.asyncio
    async def test_max_patterns_respected(self) -> None:
        config = PatternConfig(max_patterns_per_run=2)
        agent = PatternAgent(config=config)
        uid = uuid.uuid4()
        memories = [
            _make_memory("I avoid conflict", uid, days_ago=10),
            _make_memory("I avoid arguments", uid, days_ago=5),
            _make_memory("I avoid problems", uid, days_ago=1),
            _make_memory("I avoid situations", uid, days_ago=2),
            _make_memory("I feel perfect about everything always", uid, days_ago=10),
            _make_memory("Nothing is ever perfect enough for me", uid, days_ago=5),
            _make_memory("I can't accept any mistakes ever", uid, days_ago=1),
        ]
        output = await agent.execute(_context_with_memories(memories))
        total = len(output.data.get("new_patterns", [])) + len(output.data.get("updated_patterns", []))
        assert total <= 2


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------

class TestFailureHandling:
    @pytest.mark.asyncio
    async def test_graceful_failure(self, agent: PatternAgent) -> None:
        output = await agent.execute({})
        assert output.status == "failed"
        assert "error" in output.data

    @pytest.mark.asyncio
    async def test_failure_event_emitted(self, agent: PatternAgent) -> None:
        output = await agent.execute({})
        assert any(e["event_type"] == "PatternDetectionFailed" for e in output.events)


# ---------------------------------------------------------------------------
# Dataclass tests
# ---------------------------------------------------------------------------

class TestDataclasses:
    def test_detected_pattern_defaults(self) -> None:
        p = DetectedPattern(pattern_id="1", name="test", description="desc", category="cognitive")
        assert p.confidence == 0.0
        assert p.occurrence_count == 0
        assert p.trend == TrendDirection.STABLE

    def test_pattern_config_defaults(self) -> None:
        c = PatternConfig()
        assert c.min_occurrences == 2
        assert c.min_confidence == 0.3
        assert c.similarity_threshold == 0.7
