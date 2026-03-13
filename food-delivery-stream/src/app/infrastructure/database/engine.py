from sqlalchemy.ext.asyncio import create_async_engine

from src.app.core.config import settings

engine = create_async_engine(
    settings.db.database_url,
    echo=settings.app.is_dev,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)
