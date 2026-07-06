"""DEC Goal persistence model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ayeneh.infrastructure.persistence.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from ayeneh.infrastructure.persistence.types import JSONBCompat


class DECGoalModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """DEC-02 goal records — goals managed by the decision architecture."""

    __tablename__ = "dec_goals"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    goal_type: Mapped[str] = mapped_column(String(50), nullable=False, default="outcome")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    importance: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sub_goals: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    success_criteria: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    associated_plan_ids: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    parent_goal_id: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    explainability_metadata: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
