from typing import Any, Generic, TypeVar

from sqlalchemy import delete, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.logger import get_logger

T = TypeVar("T")

logger = get_logger()


class BaseRepository(Generic[T]):
    """
    generic repository.

    Responsibilities:
    - CRUD operations
    - Query building
    - Transaction-safe flush operations

    Notes:
    - Does NOT commit transactions (service layer controls commit/rollback)
    - Uses SQLAlchemy 2.0 style queries
    """

    def __init__(self, model: type[T], session: AsyncSession):
        self.model = model  # table name
        self.session = session

    # --- CREATE ---

    async def create(self, data: dict[str, Any]) -> T:
        """
        Create a new record.

        Flush is used instead of commit so that
        the service layer controls transactions.
        """
        db_obj = self.model(**data)

        self.session.add(db_obj)

        try:
            await self.session.flush()
            return db_obj

        except SQLAlchemyError as e:
            logger.error(
                "repository_create_failed",
                model=self.model.__name__,
                payload=data,
                error=str(e),
            )
            raise

    # --- UPDATE ---
    async def update(self, obj_id: Any, data: dict[str, Any]) -> T | None:
        """
        Update record using PostgreSQL RETURNING
        to avoid extra round-trip queries.
        """

        stmt = (
            update(self.model).where(self.model.id == obj_id).values(**data).returning(self.model)
        )

        try:
            result = await self.session.execute(stmt)
            return result.scalars().first()

        except SQLAlchemyError as e:
            logger.error(
                "repository_update_failed",
                model=self.model.__name__,
                id=obj_id,
                payload=data,
                error=str(e),
            )
            raise

    # --- DELETE ---

    async def delete(self, obj_id: Any) -> bool:
        """
        Hard delete a record.

        Uses RETURNING for reliability across DB drivers.
        """

        stmt = delete(self.model).where(self.model.id == obj_id).returning(self.model.id)

        try:
            result = await self.session.execute(stmt)

            return result.scalar_one_or_none() is not None

        except SQLAlchemyError as e:
            logger.error(
                "repository_delete_failed",
                model=self.model.__name__,
                id=obj_id,
                error=str(e),
            )
            raise
