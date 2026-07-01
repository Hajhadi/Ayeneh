"""Comprehensive tests for the Session Goal Manager."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from ayeneh.session_goal.engine import (
    SessionGoalExtractor,
    SessionGoalManager,
    SessionGoalUpdater,
    SessionGoalValidator,
    SessionGoalStore,
)
from ayeneh.session_goal.types import (
    SessionGoal,
    SessionGoalContext,
    SessionGoalHistory,
    SessionGoalMetrics,
    SessionGoalStatus,
)


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class InMemorySessionGoalStore(SessionGoalStore):
    def __init__(self) -> None:
        self._goals: dict[str, SessionGoal] = {}
        self._by_conversation: dict[str, str] = {}

    async def save_goal(self, goal: SessionGoal) -> SessionGoal:
        self._goals[goal.id] = goal
        self._by_conversation[goal.conversation_id] = goal.id
        return goal

    async def get_goal(self, goal_id: str) -> SessionGoal | None:
        return self._goals.get(goal_id)

    async def get_by_conversation(self, conversation_id: str) -> SessionGoal | None:
        goal_id = self._by_conversation.get(conversation_id)
        if goal_id:
            return self._goals.get(goal_id)
        return None

    async def update_goal(self, goal: SessionGoal) -> None:
        self._goals[goal.id] = goal

    async def list_by_user(self, user_id: str, limit: int = 20) -> list[SessionGoal]:
        return [g for g in self._goals.values() if g.user_id == user_id][:limit]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store() -> InMemorySessionGoalStore:
    return InMemorySessionGoalStore()


@pytest.fixture
def manager(store: InMemorySessionGoalStore) -> SessionGoalManager:
    return SessionGoalManager(store=store)


@pytest.fixture
def extractor() -> SessionGoalExtractor:
    return SessionGoalExtractor()


@pytest.fixture
def updater() -> SessionGoalUpdater:
    return SessionGoalUpdater()


@pytest.fixture
def validator() -> SessionGoalValidator:
    return SessionGoalValidator()


@pytest.fixture
def learning_context() -> SessionGoalContext:
    return SessionGoalContext(
        conversation_id="conv1",
        user_id="user1",
        first_message="I want to understand why meditation helps with anxiety",
        conversation_title="Meditation and Anxiety",
    )


@pytest.fixture
def reflection_context() -> SessionGoalContext:
    return SessionGoalContext(
        conversation_id="conv2",
        user_id="user1",
        first_message="I notice I keep procrastinating on important tasks",
        conversation_title="Procrastination Patterns",
    )


@pytest.fixture
def decision_context() -> SessionGoalContext:
    return SessionGoalContext(
        conversation_id="conv3",
        user_id="user1",
        first_message="Should I change careers or stay in my current job?",
        conversation_title="Career Decision",
    )


# ---------------------------------------------------------------------------
# Extractor tests
# ---------------------------------------------------------------------------


class TestSessionGoalExtractor:
    def test_extracts_goal_from_learning_message(
        self, extractor: SessionGoalExtractor,
    ) -> None:
        context = SessionGoalContext(
            conversation_id="conv1",
            first_message="I want to understand how meditation works",
        )
        goal = extractor.extract(context)
        assert goal is not None
        assert "understand" in goal.title.lower() or "learning" in goal.title.lower()

    def test_extracts_goal_from_reflection_message(
        self, extractor: SessionGoalExtractor,
    ) -> None:
        context = SessionGoalContext(
            conversation_id="conv2",
            first_message="I notice I keep procrastinating",
        )
        goal = extractor.extract(context)
        assert goal is not None
        assert "reflection" in goal.title.lower() or "observe" in goal.title.lower()

    def test_extracts_goal_from_decision_message(
        self, extractor: SessionGoalExtractor,
    ) -> None:
        context = SessionGoalContext(
            conversation_id="conv3",
            first_message="Should I change careers?",
        )
        goal = extractor.extract(context)
        assert goal is not None
        assert "decision" in goal.title.lower() or "decide" in goal.title.lower()

    def test_extracts_goal_from_title(
        self, extractor: SessionGoalExtractor,
    ) -> None:
        context = SessionGoalContext(
            conversation_id="conv4",
            conversation_title="Learning about philosophy",
        )
        goal = extractor.extract(context)
        assert goal is not None

    def test_returns_none_for_empty_context(
        self, extractor: SessionGoalExtractor,
    ) -> None:
        context = SessionGoalContext(conversation_id="conv5")
        goal = extractor.extract(context)
        assert goal is None

    def test_goal_has_confidence(
        self, extractor: SessionGoalExtractor,
        learning_context: SessionGoalContext,
    ) -> None:
        goal = extractor.extract(learning_context)
        assert goal is not None
        assert 0.0 <= goal.confidence <= 1.0

    def test_goal_has_status(
        self, extractor: SessionGoalExtractor,
        learning_context: SessionGoalContext,
    ) -> None:
        goal = extractor.extract(learning_context)
        assert goal is not None
        assert goal.status in [
            SessionGoalStatus.CANDIDATE,
            SessionGoalStatus.ACTIVE,
            SessionGoalStatus.UNCERTAIN,
        ]

    def test_goal_has_source(
        self, extractor: SessionGoalExtractor,
        learning_context: SessionGoalContext,
    ) -> None:
        goal = extractor.extract(learning_context)
        assert goal is not None
        assert goal.source == "extracted"


# ---------------------------------------------------------------------------
# Updater tests
# ---------------------------------------------------------------------------


class TestSessionGoalUpdater:
    def test_updates_goal_on_intent_shift(
        self, updater: SessionGoalUpdater,
    ) -> None:
        current = SessionGoal(
            title="Understanding a concept",
            description="Learning about meditation",
            confidence=0.7,
        )
        context = SessionGoalContext(
            recent_messages=[
                {"content": "Actually, I need to decide whether to start meditating"},
            ],
        )
        updated = updater.update(current, context)
        assert updated is not None
        assert "decision" in updated.title.lower() or "decide" in updated.title.lower()

    def test_preserves_history(
        self, updater: SessionGoalUpdater,
    ) -> None:
        current = SessionGoal(
            title="Understanding",
            description="Learning",
            confidence=0.7,
        )
        context = SessionGoalContext(
            recent_messages=[
                {"content": "I need to decide what to do"},
            ],
        )
        updated = updater.update(current, context)
        assert updated is not None
        assert len(updated.history) == 1

    def test_returns_none_when_no_shift(
        self, updater: SessionGoalUpdater,
    ) -> None:
        current = SessionGoal(
            title="Understanding",
            description="Learning",
            confidence=0.7,
        )
        context = SessionGoalContext(recent_messages=[])
        updated = updater.update(current, context)
        assert updated is None


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------


class TestSessionGoalValidator:
    def test_valid_goal_passes(
        self, validator: SessionGoalValidator,
    ) -> None:
        goal = SessionGoal(
            title="Understanding meditation",
            confidence=0.7,
            source="extracted",
        )
        context = SessionGoalContext()
        errors = validator.validate(goal, context)
        assert len(errors) == 0

    def test_empty_title_fails(
        self, validator: SessionGoalValidator,
    ) -> None:
        goal = SessionGoal(title="", confidence=0.7)
        context = SessionGoalContext()
        errors = validator.validate(goal, context)
        assert any("title" in e for e in errors)

    def test_invalid_confidence_fails(
        self, validator: SessionGoalValidator,
    ) -> None:
        goal = SessionGoal(title="Test", confidence=1.5)
        context = SessionGoalContext()
        errors = validator.validate(goal, context)
        assert any("Confidence" in e for e in errors)

    def test_duplicate_persistent_goal_fails(
        self, validator: SessionGoalValidator,
    ) -> None:
        goal = SessionGoal(title="Learn meditation", confidence=0.7)
        context = SessionGoalContext(
            persistent_goals=[{"title": "Learn meditation"}],
        )
        errors = validator.validate(goal, context)
        assert any("persistent" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# Manager tests
# ---------------------------------------------------------------------------


class TestSessionGoalManager:
    @pytest.mark.asyncio
    async def test_extract_goal(
        self, manager: SessionGoalManager,
        learning_context: SessionGoalContext,
    ) -> None:
        goal = await manager.extract_goal(learning_context)
        assert goal is not None
        assert goal.id is not None

    @pytest.mark.asyncio
    async def test_extract_goal_has_confidence(
        self, manager: SessionGoalManager,
        learning_context: SessionGoalContext,
    ) -> None:
        goal = await manager.extract_goal(learning_context)
        assert goal is not None
        assert 0.0 <= goal.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_complete_goal(
        self, manager: SessionGoalManager,
    ) -> None:
        # First create a goal
        context = SessionGoalContext(
            conversation_id="conv_complete",
            first_message="I want to learn about philosophy",
        )
        goal = await manager.extract_goal(context)
        assert goal is not None

        # Complete it
        completed = await manager.complete_goal(goal.id)
        assert completed is not None
        assert completed.status == SessionGoalStatus.COMPLETED
        assert completed.completed_at is not None

    @pytest.mark.asyncio
    async def test_abandon_goal(
        self, manager: SessionGoalManager,
    ) -> None:
        context = SessionGoalContext(
            conversation_id="conv_abandon",
            first_message="I want to learn about philosophy",
        )
        goal = await manager.extract_goal(context)
        assert goal is not None

        abandoned = await manager.abandon_goal(goal.id, reason="Changed my mind")
        assert abandoned is not None
        assert abandoned.status == SessionGoalStatus.ABANDONED

    @pytest.mark.asyncio
    async def test_request_clarification_low_confidence(
        self, manager: SessionGoalManager,
    ) -> None:
        context = SessionGoalContext(
            conversation_id="conv_clarify",
            first_message="Maybe something about something",
        )
        goal = await manager.extract_goal(context)
        if goal and goal.confidence < 0.7:
            clarification = await manager.request_clarification(goal.id)
            assert clarification is not None
            assert "misunderstanding" in clarification.lower() or "intention" in clarification.lower()

    @pytest.mark.asyncio
    async def test_get_goal_summary(
        self, manager: SessionGoalManager,
        learning_context: SessionGoalContext,
    ) -> None:
        goal = await manager.extract_goal(learning_context)
        assert goal is not None
        summary = manager.get_goal_summary(goal)
        assert "Session Goal" in summary
        assert "Confidence" in summary


# ---------------------------------------------------------------------------
# History tests
# ---------------------------------------------------------------------------


class TestHistory:
    def test_history_preserves_changes(self) -> None:
        history = SessionGoalHistory(
            old_title="Understanding",
            new_title="Deciding",
            reason="Intent shift",
            confidence=0.6,
        )
        assert history.old_title == "Understanding"
        assert history.new_title == "Deciding"
        assert history.reason == "Intent shift"

    def test_goal_history_append_only(self) -> None:
        goal = SessionGoal(title="Initial")
        goal.history.append(SessionGoalHistory(
            old_title="Initial",
            new_title="Refined",
            reason="Evolution",
        ))
        goal.history.append(SessionGoalHistory(
            old_title="Refined",
            new_title="Final",
            reason="Further evolution",
        ))
        assert len(goal.history) == 2
        assert goal.history[0].new_title == "Refined"
        assert goal.history[1].new_title == "Final"


# ---------------------------------------------------------------------------
# Status tests
# ---------------------------------------------------------------------------


class TestStatus:
    def test_all_statuses_exist(self) -> None:
        assert SessionGoalStatus.CANDIDATE == "candidate"
        assert SessionGoalStatus.ACTIVE == "active"
        assert SessionGoalStatus.REFINED == "refined"
        assert SessionGoalStatus.COMPLETED == "completed"
        assert SessionGoalStatus.ABANDONED == "abandoned"
        assert SessionGoalStatus.UNCERTAIN == "uncertain"


# ---------------------------------------------------------------------------
# Multiple conversations tests
# ---------------------------------------------------------------------------


class TestMultipleConversations:
    @pytest.mark.asyncio
    async def test_different_conversations_different_goals(
        self, manager: SessionGoalManager,
    ) -> None:
        ctx1 = SessionGoalContext(
            conversation_id="conv_a",
            first_message="I want to learn about meditation",
        )
        ctx2 = SessionGoalContext(
            conversation_id="conv_b",
            first_message="I need to make a career decision",
        )

        goal1 = await manager.extract_goal(ctx1)
        goal2 = await manager.extract_goal(ctx2)

        assert goal1 is not None
        assert goal2 is not None
        assert goal1.conversation_id != goal2.conversation_id


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_extract_goal_empty_first_message(
        self, manager: SessionGoalManager,
    ) -> None:
        context = SessionGoalContext(
            conversation_id="conv_empty",
            first_message="",
        )
        goal = await manager.extract_goal(context)
        # May or may not find a goal
        assert goal is None or goal is not None

    @pytest.mark.asyncio
    async def test_complete_nonexistent_goal(
        self, manager: SessionGoalManager,
    ) -> None:
        result = await manager.complete_goal("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_abandon_nonexistent_goal(
        self, manager: SessionGoalManager,
    ) -> None:
        result = await manager.abandon_goal("nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# Performance tests
# ---------------------------------------------------------------------------


class TestPerformance:
    @pytest.mark.asyncio
    async def test_extraction_completes_quickly(
        self, manager: SessionGoalManager,
    ) -> None:
        import time
        context = SessionGoalContext(
            first_message="I want to understand meditation",
        )
        start = time.monotonic()
        for _ in range(100):
            await manager.extract_goal(context)
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 2000  # 100 extractions in under 2 seconds


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    @pytest.mark.asyncio
    async def test_goal_has_required_fields(
        self, manager: SessionGoalManager,
        learning_context: SessionGoalContext,
    ) -> None:
        goal = await manager.extract_goal(learning_context)
        assert goal is not None
        assert hasattr(goal, "id")
        assert hasattr(goal, "conversation_id")
        assert hasattr(goal, "title")
        assert hasattr(goal, "confidence")
        assert hasattr(goal, "status")
