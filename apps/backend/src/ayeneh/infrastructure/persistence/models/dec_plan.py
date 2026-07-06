"""DEC Plan persistence model."""

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


class DECPlanModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """DEC-03 plan records — plans created by the planning engine."""

    __tablename__ = "dec_plans"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    plan_type: Mapped[str] = mapped_column(String(50), nullable=False, default="action")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    steps: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    associated_goal_id: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    associated_decision_id: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    estimated_duration: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    dependencies: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    risk_assessment: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    completed_steps: Mapped[int] = mapped_column(default=0)
    total_steps: Mapped[int] = mapped_column(default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    explainability_metadata: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
