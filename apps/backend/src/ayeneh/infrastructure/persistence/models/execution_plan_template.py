"""ExecutionPlanTemplate model."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ayeneh.infrastructure.persistence.base import Base, UUIDPrimaryKeyMixin
from ayeneh.infrastructure.persistence.types import JSONBCompat


class ExecutionPlanTemplateModel(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "execution_plan_templates"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_conditions: Mapped[dict] = mapped_column(JSONBCompat, nullable=False)
    agent_sequence: Mapped[dict] = mapped_column(JSONBCompat, nullable=False)
    input_bindings: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    error_strategies: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
