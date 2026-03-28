from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from src.app.models.orders.order import Order
from src.app.infrastructure.database.base import Base


class OrderItem(Base):
    """
    OrderItem Model: Captures the state of products at the moment of order.
    Essential for financial audit and customer receipts.
    """

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # ---  Snapshot Strategy ---
    product_id: Mapped[UUID] = mapped_column(pgUUID(as_uuid=True), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)

    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))

    quantity: Mapped[int] = mapped_column(nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # --- Context & Extensibility ---
    instructions: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # JSONB is 'Binary JSON'—fast to query and space-efficient
    item_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        server_default="{}",
        nullable=False,
    )
    # Link back to Parent
    order: Mapped["Order"] = relationship("Order", back_populates="items")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="check_unit_price_non_negative"),
        CheckConstraint("subtotal >= 0", name="check_subtotal_non_negative"),
    )
