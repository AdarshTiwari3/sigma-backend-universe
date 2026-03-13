from pydantic_settings import BaseSettings


class KafkaSettings(BaseSettings):
    """Configuration for Kafka Producers and Consumers."""

    KAFKA_BOOTSTRAP_SERVERS: str = "127.0.0.1:9092"
    KAFKA_ORDER_TOPIC: str = "order-events"
    KAFKA_CLIENT_ID: str = "order-service-producer"
