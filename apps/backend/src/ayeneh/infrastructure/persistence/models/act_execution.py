"""ACT Execution persistence model."""

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


class ACTExecutionModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """ACT-01 execution monitoring records."""

    __tablename__ = "act_executions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    execution_id: Mapped[str] = mapped_column(String(100), nullable=False, default="", unique=True)
    associated_plan: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    associated_goal: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    current_state: Mapped[str] = mapped_column(String(30), nullable=False, default="prepared")
    observed_progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    consumed_resources: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    detected_deviations: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    execution_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    version_history: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    explainability_metadata: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
