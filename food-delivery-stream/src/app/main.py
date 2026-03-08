import time
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response

from src.app.core.config import settings
from src.shared.logger import get_logger

logger = get_logger()


@asynccontextmanager
async def lifespan(_fastapi_app: FastAPI) -> AsyncGenerator[None, None]:
    # --- Startup Logic ---
    logger.info(
        "Services Starting",
        extra={
            "project": settings.PROJECT_NAME,
            "service": settings.SERVICE_NAME,
            "version": settings.VERSION,
            "env": settings.ENVIRONMENT,
        },
    )

    yield
    # --- Shutdown Logic ---
    logger.info("Service Shutting Down")


app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, lifespan=lifespan)


@app.middleware("http")
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


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
    }
