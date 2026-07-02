"""Initialize database tables."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sqlalchemy.ext.asyncio import create_async_engine
from ayeneh.infrastructure.persistence.base import Base
from ayeneh.infrastructure.persistence.models import *  # Import all models


async def init_db():
    engine = create_async_engine("sqlite+aiosqlite:////home/hadi/ayeneh/Ayeneh/ayeneh.db", echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully!")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())
