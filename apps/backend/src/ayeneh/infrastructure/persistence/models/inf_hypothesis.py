"""INF Hypothesis persistence model."""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ayeneh.infrastructure.persistence.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class INFHypothesisModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """INF-05 hypotheses — scientific hypotheses generated from reasoning."""

    __tablename__ = "inf_hypotheses"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    context_id: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    target_question: Mapped[str] = mapped_column(Text, nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_evidence: Mapped[str] = mapped_column(Text, default="[]")
    contradictory_evidence: Mapped[str] = mapped_column(Text, default="[]")
    competing_hypotheses: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    expected_predictions: Mapped[str] = mapped_column(Text, default="[]")
    evidence_requirements: Mapped[str] = mapped_column(Text, default="[]")
    current_status: Mapped[str] = mapped_column(String(30), default="active")
    version: Mapped[int] = mapped_column(Integer, default=1)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
