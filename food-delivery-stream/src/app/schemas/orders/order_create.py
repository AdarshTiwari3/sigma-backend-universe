from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, Field, computed_field, model_validator


class OrderItemDTO(BaseModel):
    """
    Hardened DTO for order items.
    Enforces financial invariants and proper serialization.
    """

    product_id: UUID
    product_name: str = Field(..., min_length=1, max_length=255)
    quantity: Annotated[int, Field(gt=0)]
    unit_price: Annotated[Decimal, Field(ge=0)]
    discount_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    instructions: str | None = Field(None, max_length=500)

    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_discount_logic(self) -> "OrderItemDTO":
        """
        Ensures the discount doesn't result in a negative price.
        """
        gross_total = self.unit_price * self.quantity
        if self.discount_amount > gross_total:
            raise ValueError(
                f"Discount ({self.discount_amount}) cannot exceed gross total ({gross_total})"
            )
        return self

    @computed_field
    @property
    def subtotal(self) -> Decimal:
        """
        @computed_field ensures subtotal is included in model_dump() and JSON.
        """
        return (self.unit_price * self.quantity) - self.discount_amount


class PlaceOrderCommand(BaseModel):
    """
    The 'Write' contract.
    Includes global validation to ensure all items sum correctly.
    """

    customer_id: UUID
    restaurant_id: UUID
    idempotency_key: str = Field(..., min_length=12)
    items: list[OrderItemDTO]
    total_amount: Decimal = Field(..., ge=0)

    @model_validator(mode="after")
    def validate_total_consistency(self) -> "PlaceOrderCommand":
        """Recalculates from computed subtotals to ensure financial integrity."""
        calculated_total = sum(item.subtotal for item in self.items)
        if abs(self.total_amount - calculated_total) > Decimal("0.01"):
            raise ValueError("Provided total_amount does not match sum of items.")
        return self
