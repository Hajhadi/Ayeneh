"""INT State persistence model."""

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


class INTStateModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """INT-04 unified cognitive state records."""

    __tablename__ = "int_states"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    state_id: Mapped[str] = mapped_column(String(100), nullable=False, default="", unique=True)
    active_modules: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    active_goals: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    running_workflows: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    resource_status: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    confidence_map: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    consistency_status: Mapped[str] = mapped_column(String(30), nullable=False, default="consistent")
    architecture_health: Mapped[float] = mapped_column(nullable=False, default=1.0)
    execution_snapshot: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    revision_history: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    explainability_metadata: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
