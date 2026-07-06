"""INT Communication persistence model."""

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


class INTCommunicationModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """INT-03 inter-module communication records."""

    __tablename__ = "int_communications"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    communication_id: Mapped[str] = mapped_column(String(100), nullable=False, default="", unique=True)
    source_module: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    target_module: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    message_type: Mapped[str] = mapped_column(String(30), nullable=False, default="data")
    payload: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    response_expected: Mapped[bool] = mapped_column(nullable=False, default=False)
    delivered: Mapped[bool] = mapped_column(nullable=False, default=False)
    acknowledged: Mapped[bool] = mapped_column(nullable=False, default=False)
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    version_history: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    explainability_metadata: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
