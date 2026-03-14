from src.app.infrastructure.kafka.producer import get_kafka_producer, init_kafka_producer
from src.shared.logger import get_logger

logger = get_logger()


def startup_kafka() -> None:
    try:
        init_kafka_producer()
        logger.info("kafka_producer_ready")
    except Exception as e:
        logger.error("kafka_initialization_failed", error=str(e))
        raise


def shutdown_kafka() -> None:
    try:
        producer = get_kafka_producer()

        logger.info("flushing_kafka_producer_buffer")

        remaining = producer.flush(timeout=10.0)

        if remaining > 0:
            logger.warning("kafka_flush_incomplete", missing_count=remaining)
        else:
            logger.info("kafka_flush_successful")

    except Exception as e:
        logger.error("kafka_shutdown_error", error=str(e))
