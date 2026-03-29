from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.app.exceptions.base_exceptions import AppBaseException
from src.shared.logger import get_logger

logger = get_logger()


def register_exception_handler(app: FastAPI) -> None:
    """After this we dont have to write the try/except inside controller it handles automatically"""

    # 1. Handle custom Business Logic errors
    @app.exception_handler(AppBaseException)
    async def app_base_exception(request: Request, exc: AppBaseException):
        """
        Catches any exception inheriting from AppBaseException.
        Uses the built-in to_log() and to_dict() methods.
        """

        # 1. Structured Logging (for ELK/Grafana)
        logger.error(
            "app_business_exception",
            path=request.url.path,
            method=request.method,
            **exc.to_log(),  # Captures error_code, http_status, context
        )

        # 2. Consistent API Response
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),  # Returns the exact {success: False, error: {...}} format
        )

    # 2. Handle FastAPI's built-in Schema errors (The Transformation)
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning("request_validation_failed", path=request.url.path, errors=exc.errors())

        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "The request format is incorrect.",
                    "details": {"errors": exc.errors()},  # This is the 'transformation'
                },
            },
        )

    # 3. Handle the 'Boom' (Uncaught Python crashes)
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """
        The 'Catch-All' for unexpected Python errors (DivideByZero, KeyError, etc.)
        Prevents leaking internal tracebacks to the user.
        """
        logger.fatal(
            "unhandled_system_error",
            path=request.url.path,
            error_type=type(exc).__name__,
            error_details=str(exc),
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred on our end.",
                    "details": {
                        "trace_id": getattr(request.state, "trace_id", None),
                    },
                },
            },
        )
