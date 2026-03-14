from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.app.core.config import settings
from src.app.core.lifecycle.database_lifecycle import (
    shutdown_database,
    startup_database,
)
from src.app.core.lifecycle.kafka_lifecycle import shutdown_kafka, startup_kafka
from src.app.core.lifecycle.redis_lifecycle import shutdown_redis, startup_redis
from src.shared.logger import get_logger

logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manages the application lifecycle.
    Ensures infrastructure (Kafka, DB) starts and stops gracefully.
    """

    redis_started = False
    db_started = False
    kafka_started = False

    try:

        logger.info(
            "services_starting",
            project=settings.app.PROJECT_NAME,
            version=settings.app.VERSION,
            env=settings.app.ENVIRONMENT,
        )

        await startup_redis()
        redis_started = True

        await startup_database()
        db_started = True

        startup_kafka()
        kafka_started = True

        logger.info("application_startup_complete")

        yield

    except Exception as e:
        logger.fatal("application_startup_failed", error=str(e))
        raise

    finally:
        logger.info("services_shutting_down_initiated")

        if kafka_started:
            shutdown_kafka()

        if db_started:
            await shutdown_database()

        if redis_started:
            await shutdown_redis()

        logger.info("cleanup_complete_safe_to_exit")
