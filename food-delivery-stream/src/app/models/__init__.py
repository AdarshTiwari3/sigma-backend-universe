# Exports all DB models - tables

from src.app.models.orders.order import Order
from src.app.models.orders.order_status import OrderStatus

# This makes it easy for Alembic to "see" everything at once
__all__ = ["Order", "OrderStatus"]
