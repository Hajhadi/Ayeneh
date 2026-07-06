"""SELF-01 Self-Model persistence model."""

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


class SelfModelModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """SELF-01 self-model records."""

    __tablename__ = "self_models"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    model_id: Mapped[str] = mapped_column(String(100), nullable=False, default="", unique=True)
    architecture_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    available_modules: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    module_status: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    capabilities: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    known_limitations: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    active_constraints: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    available_resources: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    revision_history: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    version_metadata: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    explainability_metadata: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
