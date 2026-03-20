import copy
from typing import Any

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.app.exceptions.orders.order_creation_exceptions import (
    OrderConflictException,
    OrderCreationFailedException,
    OrderValidationException,
)
from src.app.infrastructure.kafka.producer import KafkaProducerProvider
from src.app.infrastructure.redis.redis import RedisManager
from src.app.models.orders import Order
from src.app.models.orders.order_status import OrderStatus
from src.app.repositories.orders.order_creation_repository import OrderCreationRepository
from src.shared.logger import get_logger

logger = get_logger()


class OrderService:
    """Handles the business logic for Order lifecycle events."""

    def __init__(
        self,
        order_creation_repo: OrderCreationRepository,
        redis_manager: RedisManager,
        kafka_producer: KafkaProducerProvider,
    ):
        self.order_creation_repo = order_creation_repo
        self.redis = redis_manager.client
        self.kafka = kafka_producer

    async def place_order(self, order_request: dict[str, Any]) -> Any:
        """
        Orchestrates order creation with a 3-layer safety check:
        1. Redis Cache (Fast-fail)
        2. Database Transaction (Atomic Unit of Work)
        3. Database Unique Constraint (Final Race Condition Guard)
        """
        # 1. Early Validation
        try:
            idempotency_key = order_request.get("idempotency_key")
            #  shallow copy
            base_data = copy.copy(order_request["base_data"])
            items = order_request["items"]
            customer_id = base_data.get("customer_id")
        except KeyError as e:
            raise OrderValidationException(
                message=f"Missing required field: {str(e)}", error_code="INVALID_REQUEST_SHAPE"
            ) from e

        # 2. LAYER 1: Redis Check (The Shield)
        if idempotency_key:
            redis_key = f"idempotency:{idempotency_key}"
            # Using your RedisManager's client

            # NX=True ensures we only succeed if NO ONE else is processing this
            is_new_request = await self.redis.set(
                redis_key,
                "PROCESSING",
                nx=True,
                ex=300,  # 5 min lock, if not present we create a key
            )
            if not is_new_request:
                # We know this is a duplicate. We return Conflict from cache.
                cached_val = await self.redis.get(redis_key)
                logger.info("idempotency_block_active", key=idempotency_key)
                raise OrderConflictException(
                    message="Order already processed or in progress",
                    error_code="DUPLICATE_ORDER",
                    payload={"order_id": cached_val if cached_val != "PROCESSING" else "PENDING"},
                )

        # 3. Atomic Unit of Work
        # If the context manager fails to commit, it rolls back, then we catch it here.
        new_order = None
        try:
            async with self.order_creation_repo.session.begin():
                if idempotency_key:
                    base_data["idempotency_key"] = idempotency_key

                new_order = await self.order_creation_repo.create_order(order_data=base_data)
                await self.order_creation_repo.add_items(new_order.id, items)

                if "adjustments" in order_request:
                    await self.order_creation_repo.add_order_adjustments(
                        new_order.id, order_request["adjustments"]
                    )

                await self.order_creation_repo.record_status_transition(
                    new_order.id, OrderStatus.PENDING
                )
                # --- TRANSACTION COMMITTED SUCCESSFULLY HERE ---

            # --- ASYNC SIDE EFFECTS --- we should put kafka inside a transaction to avoid ghost event and redis lock leak
            self.kafka.publish(
                topic="order-created",
                key=str(new_order.order_number),
                value={
                    "order_id": new_order.id,
                    "order_number": new_order.order_number,
                    "customer_id": customer_id,
                    "status": OrderStatus.PENDING.value,
                    "total_amount": str(getattr(new_order, "total_amount", 0)),
                },
            )

            if idempotency_key:
                await self.redis.setex(
                    redis_key,
                    86400,  # 24 TTL
                    str(new_order.id),
                )

            logger.info(
                "order_created",
                order_id=new_order.id,
                customer_id=customer_id,
                idempotency_key=idempotency_key,
            )

            # SQLAlchemy handles the COMMIT/ROLLBACK automatically here
            return new_order

        except IntegrityError as e:

            # We can safely re-query the database.
            return await self._handle_race_condition(e, idempotency_key)

        except SQLAlchemyError as e:
            if redis_key:
                await self.redis.delete(redis_key)
            logger.error("order_db_error_cleanup_triggered", error=str(e))
            raise OrderCreationFailedException(payload={"reason": "DATABASE_ERROR"}) from e

        except Exception as e:
            # Catch-all for code crashes (AttributeErrors, etc.)
            if redis_key:
                await self.redis.delete(redis_key)
            logger.critical("unexpected_service_crash", error=str(e))
            raise e

    async def _handle_race_condition(self, e: IntegrityError, key: str) -> Any:
        """Identifies unique constraint violations and reconciles the state."""
        # Check for unique constraint violation (idempotency_key)
        if key and ("unique" in str(e).lower() or "idempotency" in str(e).lower()):
            logger.warning("idempotency_race_detected", key=key)

            # Re-fetch the record created by the concurrent winning request
            existing_order = await self.order_creation_repo.get_by_idempotency_key(key)
            if existing_order:
                await self.redis.setex(f"idempotency:{key}", 86400, str(existing_order.id))
                return await self._resolve_duplicate_response(existing_order, key)

        raise OrderCreationFailedException(payload={"reason": "INTEGRITY_VIOLATION"}) from e

    async def _resolve_duplicate_response(self, order: Order, key: str) -> Any:
        """Ensures consistent error payloads regardless of which check path was hit."""
        logger.info("resolving_duplicate_order", idempotency_key=key, order_id=order.id)

        raise OrderConflictException(
            message="Order already processed",
            error_code="DUPLICATE_ORDER",
            payload={
                "order_number": order.order_number,
                "status": order.status.value if hasattr(order.status, "value") else order.status,
                "created_at": str(order.created_at),
            },
        )
