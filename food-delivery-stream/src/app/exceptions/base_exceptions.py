from typing import Any


class AppBaseException(Exception):
    """
    The parent of all custom exceptions in the application.
    Allows for consistent error reporting across the system.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str = "GENERIC_ERROR",
        payload: Any | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.payload = payload if payload is not None else {}
        # We pass the message up to the Python Exception parent
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Used by the API layer to return a consistent JSON error."""
        return {
            "success": False,
            "error": {"code": self.error_code, "message": self.message, "details": self.payload},
        }

    def to_log(self) -> dict[str, Any]:
        """Used by the logger to capture structured error context."""
        return {
            "error_code": self.error_code,
            "http_status": self.status_code,
            "error_message": self.message,
            "context": self.payload,
        }

    def __str__(self) -> str:
        return f"{self.error_code}: {self.message}"

    def __repr__(self) -> str:
        return f"<AppBaseException {self.error_code} ({self.status_code}): {self.message}>"
