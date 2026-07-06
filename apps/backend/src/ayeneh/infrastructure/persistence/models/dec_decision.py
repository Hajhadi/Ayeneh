"""DEC Decision persistence model."""

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


class DECDecisionModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """DEC-01 decision records — decisions made by the cognitive system."""

    __tablename__ = "dec_decisions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    decision_type: Mapped[str] = mapped_column(String(50), nullable=False, default="general")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    context: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    options_considered: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    chosen_option: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reasoning: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    outcome: Mapped[str] = mapped_column(Text, nullable=False, default="")
    associated_plan_id: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    associated_goal_id: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    dependencies: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    explainability_metadata: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
