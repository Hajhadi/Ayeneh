"""Transaction manager — wraps UnitOfWork for convenience."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from ayeneh.infrastructure.persistence.unit_of_work import UnitOfWork

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from ayeneh.infrastructure.persistence.database import Database


@asynccontextmanager
async def transaction(db: Database) -> AsyncGenerator[UnitOfWork]:
    """Context manager that provides a UnitOfWork with automatic commit/rollback.

    Usage:
        async with transaction(db) as uow:
            user = await uow.users.get_by_id(user_id)
            # auto-commits on clean exit, auto-rollbacks on exception
    """
    assert db.session_factory is not None, "Database not connected"
    async with UnitOfWork(db.session_factory) as uow:
        try:
            yield uow
            await uow.commit()
        except Exception:
            await uow.rollback()
            raise
