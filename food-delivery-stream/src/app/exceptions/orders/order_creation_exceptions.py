from typing import Any

from src.app.exceptions.base_exceptions import AppBaseException


class OrderCreationException(AppBaseException):
    """Base for all errors during the order placement phase."""

    pass


class OrderValidationException(OrderCreationException):
    """Generic 422: Business logic fails (e.g., Minimum order not met)."""

    def __init__(self, message: str, error_code: str, payload: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code=error_code,
            payload=payload,
        )


class OrderConflictException(OrderCreationException):
    """Generic 409: State/Data conflicts (e.g., Idempotency or Price changes)."""

    def __init__(self, message: str, error_code: str, payload: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            status_code=409,
            error_code=error_code,
            payload=payload,
        )


class OrderPermissionException(OrderCreationException):
    """Generic 403: User/Actor is not allowed to create this order."""

    def __init__(self, message: str, error_code: str, payload: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            status_code=403,
            error_code=error_code,
            payload=payload,
        )


class OrderCreationFailedException(OrderCreationException):
    """Generic 500: Something went wrong on the server side."""

    def __init__(self, payload: dict[str, Any] | None = None):
        super().__init__(
            message="We couldn't process your order. Please try again.",
            status_code=500,
            error_code="ORDER_CREATION_FAILED",
            payload=payload,
        )
