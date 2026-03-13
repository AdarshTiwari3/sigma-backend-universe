from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.app.core.config import settings
from src.app.infrastructure.database.session import engine
from src.app.infrastructure.kafka.producer import get_kafka_producer, init_kafka_producer
from src.shared.logger import get_logger

logger = get_logger()


@asynccontextmanager
async def lifespan(_fastapi_app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manages the application lifecycle.
    Ensures infrastructure (Kafka, DB) starts and stops gracefully.
    """
    # --- Startup Logic ---
    logger.info(
        "services_starting",
        project=settings.PROJECT_NAME,
        service=settings.SERVICE_NAME,
        version=settings.VERSION,
        env=settings.ENVIRONMENT,
        kafka_broker=settings.KAFKA_BOOTSTRAP_SERVERS,
        db_host=settings.DB_HOST,
    )

    # 1. Initialize Kafka Producer
    try:
        init_kafka_producer()
        logger.info("kafka_producer_ready")
    except Exception as e:
        logger.error("kafka_initialization_failed", error=str(e))
        raise e

    yield

    # --- Shutdown Logic ---
    logger.info("services_shutting_down_initiated")

    # 1. Flush Kafka buffer
    try:
        # FIX: Access the instance via the getter function
        producer = get_kafka_producer()
        logger.info("flushing_kafka_producer_buffer")

        unfilled_messages = producer.flush(timeout=10.0)

        if unfilled_messages > 0:
            logger.warning("kafka_flush_incomplete", missing_count=unfilled_messages)
        else:
            logger.info("kafka_flush_successful")
    except Exception as e:
        logger.error("kafka_shutdown_error", error=str(e))

    # 2. Close Database connection pools
    try:
        logger.info("closing_database_connection_pool")
        # dispose() is the correct way to close all underlying connections in the pool
        await engine.dispose()
        logger.info("database_connections_closed")
    except Exception as e:
        logger.error("database_shutdown_error", error=str(e))

    logger.info("cleanup_complete_safe_to_exit")
