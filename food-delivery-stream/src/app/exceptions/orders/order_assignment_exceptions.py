from typing import Any

from src.app.exceptions.base_exceptions import AppBaseException


class OrderAssignmentException(AppBaseException):
    """Base for all errors during the driver assignment/claiming phase."""

    pass


class OrderStateConflictException(OrderAssignmentException):
    """Generic 409 for the Order Assignment domain."""

    def __init__(self, message: str, error_code: str, payload: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            status_code=409,
            error_code=error_code,
            payload=payload,
        )


class OrderPermissionException(OrderAssignmentException):
    """Generic 403 for the Order Assignment domain."""

    def __init__(self, message: str, error_code: str, payload: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            status_code=403,
            error_code=error_code,
            payload=payload,
        )


class OrderValidationException(OrderAssignmentException):
    """Generic 422 for logical business rule violations during assignment."""

    def __init__(self, message: str, error_code: str, payload: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code=error_code,
            payload=payload,
        )


class OrderNotFoundException(OrderAssignmentException):
    """The 'Missing Resource' error"""

    def __init__(self, order_id: int):
        super().__init__(
            message=f"Order {order_id} could not be found in our records.",
            status_code=404,
            error_code="ORDER_NOT_FOUND",
            payload={"order_id": order_id},
        )
