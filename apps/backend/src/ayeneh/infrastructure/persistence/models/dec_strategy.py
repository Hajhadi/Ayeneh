"""DEC Strategy persistence model."""

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


class DECStrategyModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """DEC-05 strategy records — optimized strategies in the knowledge base."""

    __tablename__ = "dec_strategies"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    hierarchy_level: Mapped[str] = mapped_column(String(30), nullable=False, default="execution")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    supported_goals: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    underlying_principles: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    supporting_evidence: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    historical_performance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    applicable_contexts: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    known_limitations: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    risk_profile: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    revision_history: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    version_metadata: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    explainability_metadata: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
