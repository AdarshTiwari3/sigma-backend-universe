from fastapi import APIRouter, status

from src.app.dependencies.orders import OrderServiceDep
from src.app.schemas.orders.order_create import OrderRequestDTO
from src.shared.logger import get_logger

logger = get_logger()
router = APIRouter()


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Place a new delivery order",
    response_description="The created order details",
)
async def place_new_order(order_request: OrderRequestDTO, order_service: OrderServiceDep):
    """
    Entry point for creating an order.

    - **Validation**: Handled by Pydantic & RequestValidationError handler.
    - **Idempotency**: Handled by OrderService via Redis.
    - **Persistence**: Handled by OrderService via Repository.
    - **Events**: Kafka message published upon success.
    """

    logger.info(
        "order_placement_attempt",
        customer_id=str(order_request.customer_id),
        idempotency_key=order_request.idempotency_key,
    )

    # All business logic (Redis locks, DB, Kafka) lives inside this call

    order = await order_service.place_order(order_request=order_request)

    return {
        "success": True,
        "message": "Order successfully placed",
        "data": {
            "order_id": str(order.id),
            "order_number": order.order_number,
            "status": order.status,
            "created_at": order.created_at.isoformat(),
        },
    }
