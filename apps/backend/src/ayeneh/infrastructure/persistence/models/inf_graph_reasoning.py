"""INF Graph Reasoning persistence model."""

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


class INFGraphReasoningModel(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """INF-02 graph reasoning sessions — graph-based reasoning over knowledge networks."""

    __tablename__ = "inf_graph_reasoning"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    context_id: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    traversal_strategy: Mapped[str] = mapped_column(String(50), default="breadth_first")
    starting_nodes: Mapped[str] = mapped_column(Text, default="[]")
    visited_nodes: Mapped[str] = mapped_column(Text, default="[]")
    visited_relationships: Mapped[str] = mapped_column(Text, default="[]")
    detected_patterns: Mapped[str] = mapped_column(Text, default="[]")
    supporting_evidence: Mapped[str] = mapped_column(Text, default="[]")
    reasoning_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    traversal_depth: Mapped[int] = mapped_column(Integer, default=0)
    alternative_paths: Mapped[str] = mapped_column(Text, default="[]")
    version: Mapped[int] = mapped_column(Integer, default=1)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
