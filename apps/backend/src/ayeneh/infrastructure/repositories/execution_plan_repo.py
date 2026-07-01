"""Execution plan repository implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ayeneh.infrastructure.persistence.models.execution_plan import ExecutionPlanModel
from ayeneh.infrastructure.repositories.base import SQLAlchemyBaseRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ExecutionPlanRepositoryImpl(SQLAlchemyBaseRepository):
    """Execution plan repository."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ExecutionPlanModel)
