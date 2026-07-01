"""Goal persistence model — SQLAlchemy model for the goals table."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ayeneh.infrastructure.persistence.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from ayeneh.infrastructure.persistence.types import JSONBCompat


class GoalModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Goals table — independent cognitive goal entities."""

    __tablename__ = "goals"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    category: Mapped[str] = mapped_column(String(20), nullable=False, default="other")
    goal_type: Mapped[str] = mapped_column(String(20), nullable=False, default="outcome")
    importance: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    relevance: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    parent_goal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("goals.id"), nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    target_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    abandoned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_progress_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    related_goal_ids: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    milestones: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    dependencies: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    confidence_history: Mapped[dict] = mapped_column(JSONBCompat, nullable=True)
    importance_history: Mapped[dict] = mapped_column(JSONBCompat, nullable=True)
    evolution_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class GoalEvolutionEventModel(Base, UUIDPrimaryKeyMixin):
    """Append-only goal evolution event log."""

    __tablename__ = "goal_evolution_events"

    goal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("goals.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GoalHistoryModel(Base, UUIDPrimaryKeyMixin):
    """Append-only goal state transition log."""

    __tablename__ = "goal_history"

    goal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("goals.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GoalReviewModel(Base, UUIDPrimaryKeyMixin):
    """Goal review records."""

    __tablename__ = "goal_reviews"

    goal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("goals.id"), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reviewer: Mapped[str] = mapped_column(String(50), nullable=False, default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
