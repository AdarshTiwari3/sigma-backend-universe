from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from src.app.models.orders.order import Order

from src.app.infrastructure.database.base import Base


class OrderAdjustment(Base):
    """
    Records taxes, delivery fees, and discounts applied to the order.
    Ensures the 'total_amount' is auditable and transparent.
    """

    __tablename__ = "order_adjustments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Type of adjustment: 'TAX', 'DELIVERY_FEE', 'PROMO_DISCOUNT'
    adjustment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))

    # Relationship
    order: Mapped["Order"] = relationship("Order", back_populates="adjustments")
