from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import JSON, CheckConstraint, DateTime, Enum, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from src.app.models.orders.order_adjustment import OrderAdjustment
    from src.app.models.orders.order_item import OrderItem
    from src.app.models.orders.order_status_history import OrderStatusHistory

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

    # NEW COLUMN FOR IDEMPOTENCY
    idempotency_key: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=True,
        comment="Unique request key to prevent duplicate processing",
    )

    # --- Financial Data ---
    # Numeric(10, 2) ensures we handle money correctly (max 99,999,999.99)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # THE LOGISTICS BRIDGE
    # Even if another service handles delivery, the Order needs to know
    # where it's going at the time of purchase (Snapshot).
    delivery_address: Mapped[dict] = mapped_column(
        JSON, nullable=False, comment="Snapshot of the address at order time"
    )

    # THE RESTAURANT IDENTIFIER
    # You cannot have an order without a vendor.
    restaurant_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)

    # THE EXTERNAL LINK
    # Nullable because we don't have a delivery_id until the Delivery Service assigns one.
    delivery_id: Mapped[str | None] = mapped_column(
        String(50),
        index=True,
        nullable=True,
        comment="Foreign reference to the Delivery Microservice",
    )

    # RELATIONSHIP TO THE SECOND TABLE
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )

    adjustments: Mapped[list["OrderAdjustment"]] = relationship(
        "OrderAdjustment", back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )

    status_history: Mapped[list["OrderStatusHistory"]] = relationship(
        "OrderStatusHistory", back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )

    # --- State Management ---
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus),
        default=OrderStatus.PENDING,
        server_default=OrderStatus.PENDING.value,
        nullable=False,
        index=True,
    )

    version: Mapped[int] = mapped_column(
        default=1,
        nullable=False,
        comment="Optimistic locking version counter",
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

    __mapper_args__ = {"version_id_col": version}

    def __repr__(self) -> str:
        """Developer-friendly string representation."""
        return (
            f"<Order(id={self.id}, " f"number='{self.order_number}', " f"status='{self.status}')>"
        )
