import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from src.app.core.config import settings
from src.shared.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup Logic ---
    logger.info(
        "Services Starting",
        extra={
            "project": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "env": settings.ENVIRONMENT,
        },
    )

    yield
    # --- Shutdown Logic ---
    logger.info("Service Shutting Down")


app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, lifespan=lifespan)


@app.middleware("http")
async def log_requests(request: Request, call_next):

    start_time = time.perf_counter()

    try:
        response = await call_next(request)
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
async def health_check():
    return {"status": "ok", "service": settings.PROJECT_NAME}
