from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Enum, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.app.infrastructure.database.base import Base
from src.app.models.orders.order_status import OrderStatus


class Order(Base):
    """
    Order Model for the Food Delivery Stream.
    Attributes:
        id: Internal Database Primary Key (Auto-indexed).
        order_number: Unique, human-readable ID (Indexed for fast lookup).
        customer_id: Reference to the user who placed the order (Indexed).
        total_amount: Final price of the order (Decimal to prevent rounding errors).
        status: The current state of the order lifecycle.

    """

    __tablename__ = "orders"

    # --- Identifiers ---
    # Postgres automatically creates a B-Tree index for Primary Keys
    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment="Internal database identifier"
    )
    # We use index=True here because the Stream/API will search by Order Number
    order_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Public-facing unique order reference",
    )

    # We use index=True here to make 'Get My Orders' queries lightning fast
    customer_id: Mapped[str] = mapped_column(
        String(50), index=True, nullable=False, comment="Identifier for the customer"
    )
    # --- Financial Data ---
    # Numeric(10, 2) ensures we handle money correctly (max 99,999,999.99)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # --- State Management ---
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus),
        default=OrderStatus.PENDING,
        server_default=OrderStatus.PENDING.value,
        nullable=False,
        index=True,
    )

    # --- Audit Timestamps ---
    # Stored in UTC with Timezone awareness
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # --- Database Guardrails ---
    __table_args__ = (
        # Prevents negative prices at the hardware/DB level
        CheckConstraint("total_amount > 0", name="check_total_amount_positive"),
    )

    def __repr__(self) -> str:
        """Developer-friendly string representation."""
        return (
            f"<Order(id={self.id}, " f"number='{self.order_number}', " f"status='{self.status}')>"
        )
