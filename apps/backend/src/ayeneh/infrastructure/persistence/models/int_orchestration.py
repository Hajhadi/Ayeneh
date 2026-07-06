"""INT Orchestration persistence model."""

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


class INTOrchestrationModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """INT-01 orchestration records."""

    __tablename__ = "int_orchestrations"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    orchestration_id: Mapped[str] = mapped_column(String(100), nullable=False, default="", unique=True)
    task_id: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    participating_modules: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    execution_graph: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    dependency_graph: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    execution_timeline: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    current_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    resource_allocation: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    final_integration_summary: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    version_history: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    explainability_metadata: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
