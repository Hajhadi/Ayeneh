"""SessionGoalManager — single owner of conversation session goals."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.session_goal.types import (
    SessionGoal,
    SessionGoalContext,
    SessionGoalHistory,
    SessionGoalMetrics,
    SessionGoalStatus,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Abstract ports
# ---------------------------------------------------------------------------


class SessionGoalStore:
    """Abstract persistence for session goals."""

    async def save_goal(self, goal: SessionGoal) -> SessionGoal:
        raise NotImplementedError

    async def get_goal(self, goal_id: str) -> SessionGoal | None:
        raise NotImplementedError

    async def get_by_conversation(self, conversation_id: str) -> SessionGoal | None:
        raise NotImplementedError

    async def update_goal(self, goal: SessionGoal) -> None:
        raise NotImplementedError

    async def list_by_user(self, user_id: str, limit: int = 20) -> list[SessionGoal]:
        raise NotImplementedError


class EventPublisher:
    """Abstract event publishing interface."""

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Session Goal Extractor
# ---------------------------------------------------------------------------


class SessionGoalExtractor:
    """Extracts session goals from conversation context.

    Never invents goals. Uses multiple signals to infer intent.
    """

    def extract(self, context: SessionGoalContext) -> SessionGoal | None:
        """Extract a session goal from context."""
        signals: list[tuple[str, float]] = []

        # Signal 1: First message analysis
        if context.first_message:
            goal_from_first, confidence = self._analyze_first_message(context.first_message)
            if goal_from_first:
                signals.append((goal_from_first, confidence * 0.4))

        # Signal 2: Conversation title
        if context.conversation_title:
            goal_from_title, confidence = self._analyze_title(context.conversation_title)
            if goal_from_title:
                signals.append((goal_from_title, confidence * 0.3))

        # Signal 3: Recent messages
        if context.recent_messages:
            goal_from_messages, confidence = self._analyze_recent_messages(context.recent_messages)
            if goal_from_messages:
                signals.append((goal_from_messages, confidence * 0.2))

        # Signal 4: Dialogue analysis
        if context.dialogue_analysis:
            goal_from_dialogue, confidence = self._analyze_dialogue(context.dialogue_analysis)
            if goal_from_dialogue:
                signals.append((goal_from_dialogue, confidence * 0.1))

        if not signals:
            return None

        # Select best signal
        signals.sort(key=lambda s: s[1], reverse=True)
        best_goal, best_confidence = signals[0]

        # Determine status based on confidence
        if best_confidence >= 0.7:
            status = SessionGoalStatus.ACTIVE
        elif best_confidence >= 0.4:
            status = SessionGoalStatus.CANDIDATE
        else:
            status = SessionGoalStatus.UNCERTAIN

        return SessionGoal(
            conversation_id=context.conversation_id,
            user_id=context.user_id,
            title=best_goal,
            description=self._build_description(best_goal, context),
            confidence=best_confidence,
            status=status,
            source="extracted",
            extraction_reason=self._build_extraction_reason(signals),
        )

    def _analyze_first_message(self, message: str) -> tuple[str, float]:
        """Analyze the first user message for intent."""
        message_lower = message.lower()

        # Question patterns
        if any(w in message_lower for w in ["what is", "what are", "how do", "why"]):
            return "Understanding a concept or process", 0.6

        # Reflection patterns
        if any(w in message_lower for w in ["i notice", "i feel", "i think", "i realize"]):
            return "Self-reflection and observation", 0.7

        # Decision patterns
        if any(w in message_lower for w in ["should i", "which", "decide", "choose"]):
            return "Making a decision", 0.7

        # Learning patterns
        if any(w in message_lower for w in ["learn", "teach", "explain", "understand"]):
            return "Learning about a topic", 0.6

        # Practice patterns
        if any(w in message_lower for w in ["practice", "exercise", "technique"]):
            return "Developing a practice or skill", 0.6

        return "Exploring a topic", 0.4

    def _analyze_title(self, title: str) -> tuple[str, float]:
        """Analyze the conversation title for intent."""
        title_lower = title.lower()

        if any(w in title_lower for w in ["question", "ask", "inquiry"]):
            return "Seeking information or clarification", 0.5

        if any(w in title_lower for w in ["reflect", "observe", "notice"]):
            return "Self-reflection and observation", 0.6

        if any(w in title_lower for w in ["decide", "choice", "option"]):
            return "Making a decision", 0.6

        return "General exploration", 0.3

    def _analyze_recent_messages(self, messages: list[dict[str, Any]]) -> tuple[str, float]:
        """Analyze recent messages for evolving intent."""
        if not messages:
            return "", 0.0

        # Look for topic shifts
        topics: list[str] = []
        for msg in messages[-5:]:
            content = msg.get("content", "").lower()
            if "understand" in content or "learn" in content:
                topics.append("learning")
            elif "feel" in content or "notice" in content:
                topics.append("reflection")
            elif "decide" in content or "choose" in content:
                topics.append("decision")

        if not topics:
            return "", 0.0

        # Most common topic
        from collections import Counter
        most_common = Counter(topics).most_common(1)[0][0]

        topic_goals = {
            "learning": "Deepening understanding of a topic",
            "reflection": "Self-reflection and observation",
            "decision": "Navigating a decision",
        }

        return topic_goals.get(most_common, ""), 0.5

    def _analyze_dialogue(self, dialogue: dict[str, Any]) -> tuple[str, float]:
        """Analyze dialogue analysis for intent signals."""
        intention = dialogue.get("user_intention", "")
        confidence = dialogue.get("intention_confidence", 0.0)

        intention_goals = {
            "self_observation": "Self-reflection and observation",
            "knowledge_seeking": "Understanding a concept",
            "decision_making": "Making a decision",
            "advice_seeking": "Seeking guidance",
            "pattern_recognition": "Recognizing patterns",
        }

        goal = intention_goals.get(intention, "")
        return goal, confidence

    def _build_description(self, goal: str, context: SessionGoalContext) -> str:
        """Build a description for the session goal."""
        parts = [goal]

        if context.first_message:
            # Extract key phrases from first message
            words = context.first_message.split()[:20]
            snippet = " ".join(words)
            if len(context.first_message.split()) > 20:
                snippet += "..."
            parts.append(f"Based on: \"{snippet}\"")

        return ". ".join(parts)

    def _build_extraction_reason(self, signals: list[tuple[str, float]]) -> str:
        """Build a reason for the extraction."""
        if not signals:
            return "No clear signals detected"

        reasons = []
        for goal, confidence in signals[:3]:
            reasons.append(f"detected intent (confidence: {confidence:.2f})")

        return "; ".join(reasons)


# ---------------------------------------------------------------------------
# Session Goal Updater
# ---------------------------------------------------------------------------


class SessionGoalUpdater:
    """Updates session goals as conversation evolves."""

    def update(
        self,
        current_goal: SessionGoal,
        context: SessionGoalContext,
    ) -> SessionGoal | None:
        """Update a session goal based on new context."""
        if not context.recent_messages:
            return None

        # Analyze if goal has shifted
        new_intent = self._detect_intent_shift(current_goal, context)

        if new_intent is None:
            return None

        # Create history entry
        history = SessionGoalHistory(
            old_title=current_goal.title,
            new_title=new_intent[0],
            old_description=current_goal.description,
            new_description=new_intent[1],
            reason=new_intent[2],
            confidence=new_intent[3],
        )

        # Update goal
        current_goal.title = new_intent[0]
        current_goal.description = new_intent[1]
        current_goal.confidence = new_intent[3]
        current_goal.status = SessionGoalStatus.REFINED
        current_goal.history.append(history)
        current_goal.updated_at = _utcnow()

        return current_goal

    def _detect_intent_shift(
        self,
        current_goal: SessionGoal,
        context: SessionGoalContext,
    ) -> tuple[str, str, str, float] | None:
        """Detect if the conversation intent has shifted."""
        if not context.recent_messages:
            return None

        # Check last few messages for new intent
        recent_text = " ".join(
            msg.get("content", "") for msg in context.recent_messages[-3:]
        ).lower()

        # Check if new intent differs from current goal
        current_title_lower = current_goal.title.lower()

        if "understand" in current_title_lower and "decide" in recent_text:
            return (
                "Making a decision",
                "The conversation has shifted from understanding to decision-making",
                "Intent shift detected in recent messages",
                0.6,
            )

        if "decision" in current_title_lower and "understand" in recent_text:
            return (
                "Understanding a concept",
                "The conversation has shifted from decision-making to understanding",
                "Intent shift detected in recent messages",
                0.6,
            )

        if "reflection" in current_title_lower and "learn" in recent_text:
            return (
                "Learning about a topic",
                "The conversation has shifted from reflection to learning",
                "Intent shift detected in recent messages",
                0.5,
            )

        return None


# ---------------------------------------------------------------------------
# Session Goal Validator
# ---------------------------------------------------------------------------


class SessionGoalValidator:
    """Validates session goals for correctness."""

    def validate(self, goal: SessionGoal, context: SessionGoalContext) -> list[str]:
        """Validate a session goal. Returns list of errors."""
        errors: list[str] = []

        # Check goal is grounded in conversation
        if not goal.title:
            errors.append("Goal title is empty")

        # Check confidence is in range
        if goal.confidence < 0.0 or goal.confidence > 1.0:
            errors.append("Confidence must be between 0.0 and 1.0")

        # Check goal is not a persistent goal
        for persistent in context.persistent_goals:
            if persistent.get("title", "").lower() == goal.title.lower():
                errors.append("Session goal should not duplicate persistent goals")

        # Check source
        if goal.source not in ("extracted", "user_stated", "inferred"):
            errors.append(f"Invalid source: {goal.source}")

        return errors


# ---------------------------------------------------------------------------
# Session Goal Manager
# ---------------------------------------------------------------------------


class SessionGoalManager:
    """Single owner of conversation session goals.

    Session Goals are temporary and independent from persistent Goals.
    """

    def __init__(
        self,
        store: SessionGoalStore | None = None,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self._store = store
        self._events = event_publisher
        self._extractor = SessionGoalExtractor()
        self._updater = SessionGoalUpdater()
        self._validator = SessionGoalValidator()
        self._metrics = SessionGoalMetrics()

    async def extract_goal(
        self,
        context: SessionGoalContext,
    ) -> SessionGoal | None:
        """Extract a session goal from conversation context."""
        start = time.monotonic()

        goal = self._extractor.extract(context)
        if goal is None:
            return None

        # Validate
        errors = self._validator.validate(goal, context)
        if errors:
            logger.warning("session_goal_validation_failed", errors=errors)

        # Store
        if self._store:
            goal = await self._store.save_goal(goal)

        # Publish event
        if self._events:
            await self._events.publish("SessionGoalExtracted", {
                "goal_id": goal.id,
                "conversation_id": goal.conversation_id,
                "title": goal.title,
                "confidence": goal.confidence,
                "status": goal.status,
            })

        duration_ms = (time.monotonic() - start) * 1000

        # Update metrics
        self._metrics.goals_extracted += 1
        self._metrics.total_extractions += 1
        self._metrics.average_confidence = (
            (self._metrics.average_confidence * (self._metrics.total_extractions - 1) + goal.confidence)
            / self._metrics.total_extractions
        )
        self._metrics.average_extraction_latency_ms = (
            (self._metrics.average_extraction_latency_ms * (self._metrics.total_extractions - 1) + duration_ms)
            / self._metrics.total_extractions
        )

        logger.info(
            "session_goal_extracted",
            goal_id=goal.id,
            title=goal.title,
            confidence=goal.confidence,
            duration_ms=round(duration_ms, 2),
        )

        return goal

    async def update_goal(
        self,
        goal_id: str,
        context: SessionGoalContext,
    ) -> SessionGoal | None:
        """Update a session goal based on evolving conversation."""
        if not self._store:
            return None

        goal = await self._store.get_goal(goal_id)
        if goal is None:
            return None

        updated = self._updater.update(goal, context)
        if updated is None:
            return None

        # Validate
        errors = self._validator.validate(updated, context)
        if errors:
            logger.warning("session_goal_update_validation_failed", errors=errors)

        # Store
        await self._store.update_goal(updated)

        # Update metrics
        self._metrics.goals_refined += 1

        # Publish event
        if self._events:
            await self._events.publish("SessionGoalUpdated", {
                "goal_id": updated.id,
                "title": updated.title,
                "confidence": updated.confidence,
                "status": updated.status,
                "history_count": len(updated.history),
            })

        logger.info(
            "session_goal_updated",
            goal_id=updated.id,
            title=updated.title,
            history_count=len(updated.history),
        )

        return updated

    async def complete_goal(
        self,
        goal_id: str,
    ) -> SessionGoal | None:
        """Mark a session goal as completed."""
        if not self._store:
            return None

        goal = await self._store.get_goal(goal_id)
        if goal is None:
            return None

        goal.status = SessionGoalStatus.COMPLETED
        goal.completed_at = _utcnow()
        goal.updated_at = _utcnow()

        await self._store.update_goal(goal)

        # Update metrics
        self._metrics.goals_completed += 1

        # Publish event
        if self._events:
            await self._events.publish("SessionGoalCompleted", {
                "goal_id": goal.id,
                "title": goal.title,
                "duration_seconds": (
                    (goal.completed_at - goal.created_at).total_seconds()
                    if goal.completed_at
                    else 0
                ),
            })

        logger.info("session_goal_completed", goal_id=goal.id)
        return goal

    async def abandon_goal(
        self,
        goal_id: str,
        reason: str = "",
    ) -> SessionGoal | None:
        """Mark a session goal as abandoned."""
        if not self._store:
            return None

        goal = await self._store.get_goal(goal_id)
        if goal is None:
            return None

        goal.status = SessionGoalStatus.ABANDONED
        goal.updated_at = _utcnow()

        # Add history entry
        history = SessionGoalHistory(
            old_title=goal.title,
            new_title=goal.title,
            reason=reason or "Goal abandoned",
            confidence=goal.confidence,
        )
        goal.history.append(history)

        await self._store.update_goal(goal)

        # Update metrics
        self._metrics.goals_abandoned += 1

        # Publish event
        if self._events:
            await self._events.publish("SessionGoalAbandoned", {
                "goal_id": goal.id,
                "title": goal.title,
                "reason": reason,
            })

        logger.info("session_goal_abandoned", goal_id=goal.id, reason=reason)
        return goal

    async def get_goal(self, goal_id: str) -> SessionGoal | None:
        """Get a session goal by ID."""
        if self._store:
            return await self._store.get_goal(goal_id)
        return None

    async def get_by_conversation(self, conversation_id: str) -> SessionGoal | None:
        """Get the session goal for a conversation."""
        if self._store:
            return await self._store.get_by_conversation(conversation_id)
        return None

    async def request_clarification(
        self,
        goal_id: str,
    ) -> str | None:
        """Generate a clarification question for low-confidence goals."""
        if not self._store:
            return None

        goal = await self._store.get_goal(goal_id)
        if goal is None:
            return None

        if goal.confidence >= 0.7:
            return None

        # Update metrics
        self._metrics.clarification_requests += 1

        # Generate clarification question
        return (
            f"I may be misunderstanding your intention. "
            f"Is your main purpose in this conversation to: {goal.title}? "
            f"Or is there something else you'd like to explore?"
        )

    def get_metrics(self) -> SessionGoalMetrics:
        """Get session goal metrics."""
        return self._metrics

    def get_goal_summary(self, goal: SessionGoal) -> str:
        """Get a concise summary of the session goal for prompt context."""
        parts = [f"Session Goal: {goal.title}"]
        parts.append(f"Confidence: {goal.confidence:.0%}")
        if goal.history:
            parts.append(f"Evolved {len(goal.history)} time(s)")
        return " | ".join(parts)


def _utcnow() -> datetime:
    """Get current UTC time."""
    return datetime.now(UTC)
