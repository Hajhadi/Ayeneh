"""ACT Intervention persistence model."""

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


class ACTInterventionModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """ACT-03 adaptive intervention records."""

    __tablename__ = "act_interventions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    intervention_id: Mapped[str] = mapped_column(String(100), nullable=False, default="", unique=True)
    intervention_type: Mapped[str] = mapped_column(String(30), nullable=False, default="adaptive")
    trigger_condition: Mapped[str] = mapped_column(Text, nullable=False, default="")
    target_module: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    action_description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    expected_impact: Mapped[str] = mapped_column(Text, nullable=False, default="")
    actual_impact: Mapped[str] = mapped_column(Text, nullable=False, default="")
    success: Mapped[bool] = mapped_column(nullable=False, default=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    execution_context: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    results: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    version_history: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    explainability_metadata: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
