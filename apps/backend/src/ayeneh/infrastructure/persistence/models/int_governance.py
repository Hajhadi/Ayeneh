"""INT Governance persistence model."""

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


class INTGovernanceModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """INT-05 system governance records."""

    __tablename__ = "int_governances"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    governance_id: Mapped[str] = mapped_column(String(100), nullable=False, default="", unique=True)
    policy_reference: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    affected_modules: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    lifecycle_stage: Mapped[str] = mapped_column(String(30), nullable=False, default="normal_operation")
    decision: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    supporting_evidence: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    constraint_evaluation: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
    approval_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    audit_trail: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    version_history: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=list)
    explainability_metadata: Mapped[dict] = mapped_column(JSONBCompat, nullable=False, default=dict)
