"""ACT Habit persistence model."""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ayeneh.infrastructure.persistence.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from ayeneh.infrastructure.persistence.types import JSONBCompat


class ACTHabitModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """ACT-02 habit formation records."""

    __tablename__ = "act_habits"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    habit_id: Mapped[str] = mapped_column(String(100), nullable=False, default="", unique=True)
    habit_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    habit_type: Mapped[str] = mapped_column(String(30), nullable=False, default="behavioral")
    trigger: Mapped[str] = mapped_column(Text, nullable=False, default="")
    routine: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reward: Mapped[str] = mapped_column(Text, nullable=False, default="")
    current_streak: Mapped[int] = mapped_column(nullable=False, default=0)
    longest_streak: Mapped[int] = mapped_column(nullable=False, default=0)
    completion_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="forming")
    evidence: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    version_history: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    explainability_metadata: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
