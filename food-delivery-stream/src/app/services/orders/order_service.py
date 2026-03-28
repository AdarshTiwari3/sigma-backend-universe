from typing import Any
from uuid import uuid4

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
from src.app.schemas.orders.order_create import OrderRequestDTO
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

    async def place_order(self, order_request: OrderRequestDTO) -> Order:
        """
        Main CQRS Command Handler.
        Orchestrates Order Creation with distributed locking and atomic persistence.
        """
        # 1. Setup Context (Define variables early to avoid scope errors)
        idempotency_key = order_request.idempotency_key
        redis_key = f"idempotency:{idempotency_key}" if idempotency_key else None

        try:
            # 2. Infrastructure Guard (Redis Shield)
            await self._acquire_idempotency_lock(redis_key)

            # 3. Atomic Persistence (Pure DB Transaction)
            new_order = await self._persist_order_to_db(order_request)

            # 4. Post-Commit Side Effects (Kafka & Cache Sync)
            await self._dispatch_post_commit_events(
                new_order,
                redis_key,
                order_request,
            )

            return new_order

        except (OrderValidationException, OrderConflictException):
            # Known business errors: raise immediately, don't trigger cleanup
            raise
        except Exception as e:
            # The Janitor: Handles cleanup and error translation
            await self._janitor_cleanup(e, redis_key, idempotency_key)
            raise

    # --- PHASE 1: INFRASTRUCTURE GUARDS ---
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

    # --- PHASE 2: ATOMIC PERSISTENCE ---
    async def _persist_order_to_db(self, order_request: OrderRequestDTO) -> Order:
        """
        Converts DTO into DB Model and persists items atomically.
        """
        # Prepare base data dict for the Repo
        base_data = {
            "order_number": self._generate_order_number(),
            "customer_id": str(order_request.customer_id),
            "restaurant_id": str(order_request.restaurant_id),
            "total_amount": order_request.total_amount,
            "idempotency_key": order_request.idempotency_key,
            "delivery_address": order_request.delivery_address.model_dump(),
            "status": OrderStatus.PENDING,
        }

        items_payload = [
            item.model_dump() for item in order_request.items
        ]  # serialize in json from pydantic

        async with self.order_creation_repo.session.begin():
            # Create Order Header
            order = await self.order_creation_repo.create_order(order_data=base_data)

            # Map Items (pydantic model_dump handles the @computed_field subtotal)
            items_payload = [item.model_dump() for item in order_request.items]
            await self.order_creation_repo.add_items(order.id, items_payload)

            # Audit Trail entry
            await self.order_creation_repo.record_status_transition(order.id, OrderStatus.PENDING)

            return order

    def _generate_order_number(self) -> str:
        return f"ORD-{uuid4().hex[:12].upper()}"

    # --- PHASE 3: SIDE EFFECTS ---
    async def _dispatch_post_commit_events(
        self, order: Order, redis_key: str, order_request: OrderRequestDTO
    ) -> None:
        """Publishes to Kafka and updates final Redis state after DB success."""
        try:
            self.kafka.publish(
                topic="order-created",
                key=str(order.order_number),
                value={
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "customer_id": str(order_request.customer_id),
                    "status": OrderStatus.PENDING.value,
                    "delivery_address": order_request.delivery_address.model_dump(),
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
