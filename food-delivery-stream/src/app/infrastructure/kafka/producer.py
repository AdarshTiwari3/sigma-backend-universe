import json
from typing import Any

from confluent_kafka import Producer
from opentelemetry.propagate import inject

from src.app.core.config import settings
from src.shared.logger import get_logger

logger = get_logger()


class KafkaProducerProvider:
    """
    Production-grade Kafka Producer for the Order Service.
    Configured for high concurrency and zero data loss.
    """

    def __init__(self) -> None:

        self._conf = {
            "bootstrap.servers": settings.kafka.KAFKA_BOOTSTRAP_SERVERS,
            "client.id": settings.kafka.KAFKA_CLIENT_ID,
            "acks": "all",  # Ensure all replicas acknowledge (No data loss)
            "enable.idempotence": True,  # Prevent duplicate messages
            "compression.type": "snappy",  # High-performance compression
            "linger.ms": 5,  # Batch messages for higher throughput
        }

        try:
            self._producer = Producer(self._conf)
            logger.info(
                "kafka_producer_initialized", servers=settings.kafka.KAFKA_BOOTSTRAP_SERVERS
            )

        except Exception as e:
            logger.error("kafka_producer_init_failed", error=str(e))
            raise

    def _delivery_report(self, err: Any | None, msg: Any) -> None:
        """
        The 'Post-Office Receipt'.
        Triggered once Kafka confirms the message is safely on disk.
        """
        if err is not None:
            logger.error("kafka_delivery_failed", error=str(err), topic=msg.topic())
        else:
            logger.info(
                "kafka_message_delivered",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset(),
            )

    def publish(self, topic: str, key: str, value: dict[str, Any]) -> None:
        """
        Asynchronously push a message to a Kafka topic.

        """
        # 1. Capture Trace Context from current execution
        carrier: dict[str, str] = {}
        inject(carrier)

        # 2. Format headers as a list of tuples (Key, Bytes)
        # This is the industry standard for confluent-kafka to ensure delivery
        kafka_headers = [
            (k, v.encode("utf-8") if isinstance(v, str) else v) for k, v in carrier.items()
        ]

        try:
            # Convert Dictionary to JSON Bytes
            payload = json.dumps(value).encode("utf-8")

            # Push to the internal C-buffer
            self._producer.produce(
                topic=topic,
                key=key,
                value=payload,
                headers=kafka_headers,
                callback=self._delivery_report,
            )

        except BufferError:
            # Producer queue is full
            logger.warning(
                "kafka_buffer_full_retrying",
                topic=topic,
            )

            # Poll to process delivery callbacks and free buffer
            self._producer.poll(1)

            # Retry produce
            self._producer.produce(
                topic=topic,
                key=key,
                value=payload,
                headers=kafka_headers,
                callback=self._delivery_report,
            )

        except Exception:
            logger.error(
                "kafka_publish_exception",
                topic=topic,
            )

        finally:
            # Serve delivery report callbacks
            self._producer.poll(0)

    def flush(self, timeout: float = 10.0) -> int:
        """
        Block until all pending messages are sent.
        Crucial for clean shutdowns.
        """
        return self._producer.flush(timeout)


# --- THE SINGLETON ---
# --- SINGLETON MANAGEMENT ---
_instance: KafkaProducerProvider | None = None


def init_kafka_producer() -> KafkaProducerProvider:
    """Only called in main.py lifespan startup"""
    global _instance
    if _instance is None:
        _instance = KafkaProducerProvider()
    return _instance


def get_kafka_producer() -> KafkaProducerProvider:
    """Used by service layers to get the active producer"""
    assert _instance is not None, "Kafka Producer must be initialized in lifespan before use"
    return _instance
