"""INF Multi-Hop Reasoning persistence model."""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ayeneh.infrastructure.persistence.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class INFMultiHopModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """INF-03 multi-hop reasoning chains — recursive reasoning across cognitive dimensions."""

    __tablename__ = "inf_multihop"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    context_id: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    starting_observation: Mapped[str] = mapped_column(Text, nullable=False)
    hops: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    depth: Mapped[int] = mapped_column(Integer, default=0)
    alternative_chains: Mapped[str] = mapped_column(Text, default="[]")
    hidden_patterns: Mapped[str] = mapped_column(Text, default="[]")
    version: Mapped[int] = mapped_column(Integer, default=1)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
