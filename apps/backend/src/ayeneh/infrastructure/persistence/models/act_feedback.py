"""ACT Feedback persistence model."""

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


class ACTFeedbackModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """ACT-04 feedback loop records."""

    __tablename__ = "act_feedbacks"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    feedback_id: Mapped[str] = mapped_column(String(100), nullable=False, default="", unique=True)
    source_event: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    feedback_type: Mapped[str] = mapped_column(String(30), nullable=False, default="behavioral")
    affected_modules: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    observed_evidence: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    learning_outcome: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    propagation_targets: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    applied_revisions: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    remaining_questions: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    version_history: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    explainability_metadata: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
