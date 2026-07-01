"""Add epistemic_profiles table.

Revision ID: 002
Revises: 001
Create Date: 2025-01-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "epistemic_profiles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("book_id", sa.Uuid(), sa.ForeignKey("books.id"), nullable=False, unique=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        # Identity
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("tradition", sa.String(255), nullable=False),
        sa.Column("framework", sa.String(30), nullable=False),
        sa.Column("discipline", sa.String(30), nullable=False),
        # Topics
        sa.Column("primary_topics", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("secondary_topics", postgresql.JSONB(), nullable=False, server_default="[]"),
        # Question support
        sa.Column("supported_questions", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("unsupported_questions", postgresql.JSONB(), nullable=False, server_default="[]"),
        # Epistemic properties
        sa.Column("evidence_level", sa.String(30), nullable=False),
        sa.Column("reasoning_style", sa.String(30), nullable=False),
        sa.Column("authority", sa.String(30), nullable=False),
        sa.Column("claim_types", postgresql.JSONB(), nullable=False, server_default="[]"),
        # Scope
        sa.Column("applicability", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("limitations", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("scope_boundary", postgresql.JSONB(), nullable=False, server_default="{}"),
        # Policy
        sa.Column("citation_policy", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("confidence_policy", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("conflict_policy", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("priority_hints", postgresql.JSONB(), nullable=False, server_default="[]"),
        # Source metadata
        sa.Column("source_reliability", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("historical_period", sa.String(100), nullable=True),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("translation_metadata", postgresql.JSONB(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_epistemic_profiles_user_id", "epistemic_profiles", ["user_id"])
    op.create_index("ix_epistemic_profiles_book_id", "epistemic_profiles", ["book_id"], unique=True)
    op.create_index("ix_epistemic_profiles_discipline", "epistemic_profiles", ["discipline"])


def downgrade() -> None:
    op.drop_table("epistemic_profiles")
