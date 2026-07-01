"""Session Goal types — core domain objects for conversation session goals."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SessionGoalStatus(StrEnum):
    """Status of a session goal."""

    CANDIDATE = "candidate"
    ACTIVE = "active"
    REFINED = "refined"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    UNCERTAIN = "uncertain"


# ---------------------------------------------------------------------------
# Session Goal
# ---------------------------------------------------------------------------


@dataclass
class SessionGoal:
    """A temporary goal for a single conversation session.

    Session Goals are independent from persistent Goals.
    They live only for one dialogue session.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str = ""
    user_id: str = ""

    # Goal content
    title: str = ""
    description: str = ""
    confidence: float = 0.5
    status: str = SessionGoalStatus.CANDIDATE

    # Source
    source: str = "extracted"  # "extracted" | "user_stated" | "inferred"
    extraction_reason: str = ""

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    # History
    history: list[SessionGoalHistory] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Session Goal History
# ---------------------------------------------------------------------------


@dataclass
class SessionGoalHistory:
    """Record of a session goal change."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    old_title: str = ""
    new_title: str = ""
    old_description: str = ""
    new_description: str = ""
    reason: str = ""
    confidence: float = 0.5
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Session Goal Context
# ---------------------------------------------------------------------------


@dataclass
class SessionGoalContext:
    """Context for session goal extraction and updating."""

    conversation_id: str = ""
    user_id: str = ""

    # Conversation content
    first_message: str = ""
    conversation_title: str = ""
    message_count: int = 0
    recent_messages: list[dict[str, Any]] = field(default_factory=list)

    # External context
    persistent_goals: list[dict[str, Any]] = field(default_factory=list)
    product_profile: dict = field(default_factory=dict)
    dialogue_analysis: dict = field(default_factory=dict)
    reasoning_analysis: dict = field(default_factory=dict)

    # Current state
    current_session_goal: SessionGoal | None = None


# ---------------------------------------------------------------------------
# Session Goal Metrics
# ---------------------------------------------------------------------------


@dataclass
class SessionGoalMetrics:
    """Metrics about session goal operations."""

    goals_extracted: int = 0
    goals_refined: int = 0
    goals_completed: int = 0
    goals_abandoned: int = 0
    clarification_requests: int = 0
    average_confidence: float = 0.0
    average_extraction_latency_ms: float = 0.0
    total_extractions: int = 0
