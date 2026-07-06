"""DEC Action Evaluation persistence model."""

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


class DECActionEvaluationModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """DEC-04 action evaluation records — evaluations of executed actions."""

    __tablename__ = "dec_action_evaluations"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    associated_action: Mapped[str] = mapped_column(Text, nullable=False, default="")
    associated_plan: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    associated_goal: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    expected_outcome: Mapped[str] = mapped_column(Text, nullable=False, default="")
    observed_outcome: Mapped[str] = mapped_column(Text, nullable=False, default="")
    outcome_category: Mapped[str] = mapped_column(String(30), nullable=False, default="inconclusive")
    deviation_analysis: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    supporting_evidence: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    lessons_learned: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recommended_revisions: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    explainability_metadata: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
