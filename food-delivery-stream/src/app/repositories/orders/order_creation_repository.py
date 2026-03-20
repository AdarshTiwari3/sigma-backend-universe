from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.orders.order import Order
from src.app.models.orders.order_adjustment import OrderAdjustment
from src.app.models.orders.order_item import OrderItem
from src.app.models.orders.order_status import OrderStatus
from src.app.models.orders.order_status_history import OrderStatusHistory
from src.app.repositories.base import BaseRepository


class OrderCreationRepository(BaseRepository[Order]):
    """
    Inherits from BaseRepository.
    Uses self._session and self._model from the parent class.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(Order, session)

    async def get_by_idempotency_key(self, idempotency_key: str) -> Order | None:
        """
        Check for an existing order using the unique request key.
        This is a 'Guard Read' to prevent duplicate command execution.
        """

        query = select(Order).where(Order.idempotency_key == idempotency_key)

        result = await self.session.execute(query)

        # It returns the object if found, None if not
        return result.scalar_one_or_none()

    async def create_order(self, order_data: dict) -> Order:
        """
        Create the core Order shell.
        Uses the version column for Optimistic Locking.
        """

        new_order = Order(**order_data)

        self.session.add(new_order)
        # Flush pushes to DB to generate ID but DOES NOT commit yet
        await self.session.flush()
        return new_order

    async def add_items(self, order_id: int, items_data: list[dict[str, Any]]) -> None:
        """Add Items associated with a particular order"""
        items = [OrderItem(order_id=order_id, **item) for item in items_data]

        self.session.add_all(items)

    async def add_order_adjustments(
        self, order_id: int, adjustment_data: list[dict[str, Any]]
    ) -> None:
        """Add taxes, fees, or discounts"""

        adjustments = [
            OrderAdjustment(order_id=order_id, **adjustment) for adjustment in adjustment_data
        ]

        self.session.add_all(adjustments)

    async def record_status_transition(self, order_id: int, status: OrderStatus) -> None:
        """Audit trail for the order state lifecycle."""
        history = OrderStatusHistory(order_id=order_id, old_status=None, new_status=status)

        self.session.add(history)
