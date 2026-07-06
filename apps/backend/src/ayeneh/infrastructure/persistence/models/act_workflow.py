"""ACT Workflow persistence model."""

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


class ACTWorkflowModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """ACT-05 autonomous workflow records."""

    __tablename__ = "act_workflows"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    workflow_id: Mapped[str] = mapped_column(String(100), nullable=False, default="", unique=True)
    associated_goals: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    associated_plans: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    current_phase: Mapped[str] = mapped_column(String(30), nullable=False, default="initialization")
    current_status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    execution_history: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    dependencies: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    responsible_modules: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    priority: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    version_history: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    explainability_metadata: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
