"""SELF-02 Identity Continuity persistence model."""

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


class SelfIdentityModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """SELF-02 identity continuity records."""

    __tablename__ = "self_identities"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    identity_id: Mapped[str] = mapped_column(String(100), nullable=False, default="", unique=True)
    identity_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    core_principles: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    stable_characteristics: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    adaptive_characteristics: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    historical_lineage: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    revision_history: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    supporting_evidence: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    known_tensions: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    future_review_points: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    explainability_metadata: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
