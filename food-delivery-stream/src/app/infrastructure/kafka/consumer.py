import json

from confluent_kafka import Consumer, KafkaError, KafkaException

from src.app.core.config import settings
from src.shared.logger import get_logger

logger = get_logger()


class PaymentConsumer:
    """
    Sample Consumer for a Payment Service.
    Listens for 'OrderCreated' events to trigger payment processing.
    """

    def __init__(self):
        self._conf = {
            "bootstrap.servers": settings.kafka.KAFKA_BOOTSTRAP_SERVERS,
            "group.id": "payment-service-group",  # Shared ID for scaling
            "auto.offset.reset": "earliest",  # Start from beginning if new group
            "enable.auto.commit": False,  # Manual commit for safety
        }
        self._consumer = Consumer(self._conf)

    def subscribe(self, topics: list[str]):
        """Connects the consumer to specific topics."""
        self._consumer.subscribe(topics)
        logger.info("kafka_consumer_subscribed", topics=topics)

    def start_listening(self):
        """The main loop that waits for messages."""
        try:
            while True:
                # Wait for a message (1.0 second timeout)
                msg = self._consumer.poll(timeout=1.0)

                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        raise KafkaException(msg.error())

                # --- BUSINESS LOGIC START ---
                event_data = json.loads(msg.value().decode("utf-8"))
                logger.info("received_order_event", order_id=event_data.get("id"))

                # Logic: Trigger actual payment gateway here...
                # process_payment(event_data)

                # --- BUSINESS LOGIC END ---

                # 'Commit' tells Kafka: "I have successfully processed this message"
                self._consumer.commit(asynchronous=False)

        except KeyboardInterrupt:
            logger.info("consumer_stopping_manually")
        finally:
            self._consumer.close()


# In a worker script, you would run it like this:
# consumer = PaymentConsumer()
# consumer.subscribe([settings.kafka.KAFKA_ORDER_TOPIC])
# consumer.start_listening()
