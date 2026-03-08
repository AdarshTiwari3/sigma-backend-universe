from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.app.infrastructure.database.engine import engine

ASYNC_SESSION_FACTORY = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with ASYNC_SESSION_FACTORY() as db:
        try:
            yield db
        except Exception:
            await db.rollback()
            raise


DbSession = Annotated[AsyncSession, Depends(get_db)]
