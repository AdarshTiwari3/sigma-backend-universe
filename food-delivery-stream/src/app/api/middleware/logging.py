import time
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response

from src.shared.logger import get_logger

logger = get_logger()


async def log_requests(request: Request, call_next: Callable[[Request], Any]) -> Response:

    start_time = time.perf_counter()

    try:
        response: Response = await call_next(request)
    except Exception:
        logger.error(
            "http_request_failed",
            method=request.method,
            path=request.url.path,
        )
        raise

    process_time = time.perf_counter() - start_time

    logger.info(
        "http_request_processed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration=f"{process_time:.4f}s",
        client_ip=request.client.host if request.client else None,
    )

    return response
