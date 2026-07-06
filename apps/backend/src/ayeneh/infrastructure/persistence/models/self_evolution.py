"""SELF-05 Self-Evolution persistence model."""

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


class SelfEvolutionModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """SELF-05 self-evolution records."""

    __tablename__ = "self_evolution"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    evolution_id: Mapped[str] = mapped_column(String(100), nullable=False, default="", unique=True)
    architecture_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    proposal: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    motivation: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    supporting_evidence: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    affected_modules: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    expected_benefits: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    known_risks: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    approval_status: Mapped[str] = mapped_column(String(30), nullable=False, default="proposed")
    implementation_history: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    version_metadata: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    explainability_metadata: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
