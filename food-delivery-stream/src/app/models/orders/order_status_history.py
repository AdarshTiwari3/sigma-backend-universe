from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from src.app.models.orders.order import Order

from src.app.infrastructure.database.base import Base
from src.app.models.orders.order_status import OrderStatus


class OrderStatusHistory(Base):
    """
    Audit log for every status change.
    Essential for tracking 'Time to Prepare' or 'Time to Deliver'.
    """

    __tablename__ = "order_status_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )

    old_status: Mapped[OrderStatus | None] = mapped_column(Enum(OrderStatus))
    new_status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), nullable=False)

    # you'd also track 'changed_by' (system, driver, or restaurant)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    order: Mapped["Order"] = relationship("Order", back_populates="status_history")
