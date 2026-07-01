"""Prompt template repository implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from ayeneh.infrastructure.persistence.models.prompt_template import PromptTemplateModel
from ayeneh.infrastructure.repositories.base import SQLAlchemyBaseRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class PromptTemplateRepositoryImpl(SQLAlchemyBaseRepository):
    """Prompt template repository with active template lookup."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PromptTemplateModel)

    async def get_active_by_task_type(self, task_type: str) -> PromptTemplateModel | None:
        stmt = select(PromptTemplateModel).where(
            PromptTemplateModel.task_type == task_type,
            PromptTemplateModel.is_active.is_(True),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
