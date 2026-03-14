from src.app.infrastructure.redis.redis import redis_manager
from src.shared.logger import get_logger

logger = get_logger()


async def startup_redis() -> None:
    """Redis Startup logic"""
    try:
        await redis_manager.connect()
        logger.info("redis_ready")
    except Exception as e:
        logger.error("redis_initialization_failed", error=str(e))
        raise


async def shutdown_redis() -> None:
    """Redis Shutdown logic"""
    try:
        await redis_manager.disconnect()
        logger.info("redis_shutdown_complete")
    except Exception as e:
        logger.error("redis_shutdown_error", error=str(e))
