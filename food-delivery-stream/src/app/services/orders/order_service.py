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
from src.app.models.orders.order import Order
from src.app.models.orders.order_status import OrderStatus
from src.app.repositories.orders.order_creation_repository import OrderCreationRepository
from src.shared.logger import get_logger

logger = get_logger()


class OrderService:
    def __init__(
        self,
        order_creation_repo: OrderCreationRepository,
        redis_manager: RedisManager,
        kafka_producer: KafkaProducerProvider,
    ):
        self.order_creation_repo = order_creation_repo
        self.redis = redis_manager.client
        self.kafka = kafka_producer

    async def place_order(self, order_request: dict[str, Any]) -> Order:
        """
        Main Orchestrator.
        Logic is split into 5 distinct phases for PBC-grade readability.
        """
        # 1. Setup Context (Define variables early to avoid scope errors)
        idempotency_key = order_request.get("idempotency_key")
        redis_key = f"idempotency:{idempotency_key}" if idempotency_key else None

        # 2. Validation Phase
        base_data, items, customer_id = self._validate_request(order_request)

        try:
            # 3. Infrastructure Guard (Redis Shield)
            await self._acquire_idempotency_lock(redis_key)

            # 4. Atomic Persistence (Pure DB Transaction)
            new_order = await self._persist_order_to_db(order_request, base_data, idempotency_key)

            # 5. Post-Commit Side Effects (Kafka & Cache Sync)
            await self._dispatch_post_commit_events(new_order, redis_key, customer_id)

            return new_order

        except (OrderValidationException, OrderConflictException):
            # Known business errors: raise immediately, don't trigger cleanup
            raise
        except Exception as e:
            # The Janitor: Handles cleanup and error translation
            await self._janitor_cleanup(e, redis_key, idempotency_key)
            raise

    # --- PHASE 1: VALIDATION ---
    def _validate_request(self, request: dict) -> tuple[dict, list, Any]:
        """Ensures the incoming request has the required shape."""
        try:
            base_data = copy.copy(request["base_data"])
            return base_data, request["items"], base_data["customer_id"]
        except KeyError as e:
            raise OrderValidationException(
                message=f"Missing field: {str(e)}", error_code="INVALID_REQUEST_SHAPE"
            ) from e

    # --- PHASE 2: INFRASTRUCTURE GUARDS ---
    async def _acquire_idempotency_lock(self, redis_key: str | None) -> None:
        """Guards against concurrent duplicate requests."""
        if not redis_key:
            return

        is_new = await self.redis.set(redis_key, "PROCESSING", nx=True, ex=300)
        if not is_new:
            cached = await self.redis.get(redis_key)
            logger.info("idempotency_block_active", key=redis_key)
            raise OrderConflictException(
                message="Order already processed or in progress",
                error_code="DUPLICATE_ORDER",
                payload={"order_id": cached if cached != "PROCESSING" else "PENDING"},
            )

    # --- PHASE 3: ATOMIC PERSISTENCE ---
    async def _persist_order_to_db(self, req: dict, base: dict, key: str | None) -> Order:
        """Handles pure Database work inside an atomic block."""
        if key:
            base["idempotency_key"] = key

        async with self.order_creation_repo.session.begin():
            order = await self.order_creation_repo.create_order(order_data=base)
            await self.order_creation_repo.add_items(order.id, req["items"])

            if "adjustments" in req:
                await self.order_creation_repo.add_order_adjustments(order.id, req["adjustments"])

            await self.order_creation_repo.record_status_transition(order.id, OrderStatus.PENDING)
            return order

    # --- PHASE 4: SIDE EFFECTS ---
    async def _dispatch_post_commit_events(
        self, order: Order, redis_key: str | None, customer_id: Any
    ) -> None:
        """Handles reliable notifications and cache updates after DB success."""
        # 1. Kafka: Wait for delivery confirmation
        try:
            self.kafka.publish(
                topic="order-created",
                key=str(order.order_number),
                value={
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "customer_id": customer_id,
                    "status": OrderStatus.PENDING.value,
                },
            )
            self.kafka.flush(timeout=1.0)
        except Exception as k_err:
            logger.error("kafka_failed_after_commit", order_id=order.id, error=str(k_err))

        # 2. Redis: Sync the final ID
        if redis_key:
            await self.redis.setex(redis_key, 86400, str(order.id))

    # --- PHASE 5: ERROR RECOVERY (THE JANITOR: Cleanup) ---
    async def _janitor_cleanup(self, e: Exception, redis_key: str | None, key: str | None) -> None:
        """Ensures system state is cleaned up and errors are translated correctly."""
        if redis_key:
            await self.redis.delete(redis_key)

        if isinstance(e, IntegrityError) and key:
            # Handle race conditions where two requests bypassed Redis
            existing = await self.order_creation_repo.get_by_idempotency_key(key)
            if existing:
                await self.redis.setex(f"idempotency:{key}", 86400, str(existing.id))
                return await self._resolve_duplicate_response(existing, key)

        if isinstance(e, SQLAlchemyError):
            logger.error("db_failure", error=str(e))
            raise OrderCreationFailedException(payload={"reason": "DATABASE_ERROR"}) from e

        logger.fatal("unexpected_system_failure", error=str(e))

    # --- STANDARDIZED RESPONSE HELPER ---
    async def _resolve_duplicate_response(self, order: Order, key: str) -> Any:
        """Ensures consistent duplicate error payloads regardless of which check path was hit."""
        logger.info("resolving_duplicate_order", idempotency_key=key, order_id=order.id)

        raise OrderConflictException(
            message="Order already processed",
            error_code="DUPLICATE_ORDER",
            payload={
                "order_number": order.order_number,
                "status": order.status.value if hasattr(order.status, "value") else order.status,
                "created_at": str(getattr(order, "created_at", "N/A")),
            },
        )
