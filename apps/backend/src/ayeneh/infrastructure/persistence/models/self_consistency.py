"""SELF-04 Self-Consistency persistence model."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from ayeneh.infrastructure.persistence.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from ayeneh.infrastructure.persistence.types import JSONBCompat


class SelfConsistencyModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """SELF-04 self-consistency records."""

    __tablename__ = "self_consistency"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    consistency_id: Mapped[str] = mapped_column(String(100), nullable=False, default="", unique=True)
    affected_modules: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    consistency_type: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    supporting_evidence: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    detected_conflicts: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    resolution_status: Mapped[str] = mapped_column(String(30), nullable=False, default="unresolved")
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    revision_history: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    architectural_impact: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    recommended_actions: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    explainability_metadata: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
