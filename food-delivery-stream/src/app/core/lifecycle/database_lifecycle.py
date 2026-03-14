from sqlalchemy import text

from src.app.infrastructure.database.session import engine
from src.shared.logger import get_logger

logger = get_logger()


async def startup_database() -> None:
    try:
        logger.info("verifying_database_connection")

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        logger.info("database_connection_verified")

    except Exception as e:
        logger.error("database_initialization_failed", error=str(e))
        raise


async def shutdown_database() -> None:
    try:
        logger.info("closing_database_connection_pool")
        await engine.dispose()
        logger.info("database_connections_closed")

    except Exception as e:
        logger.error("database_shutdown_error", error=str(e))
