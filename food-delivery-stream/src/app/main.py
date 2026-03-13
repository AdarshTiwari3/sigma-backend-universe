from fastapi import FastAPI

from src.app.api.middleware.logging import log_requests
from src.app.api.v1.router import api_v1_router
from src.app.core.config import settings
from src.app.core.lifespan import lifespan
from src.app.core.tracing import setup_tracing


def create_app() -> FastAPI:

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    # 1. Setup Observability/Tracing
    setup_tracing(app)

    # 2. Register Middleware
    app.middleware("http")(log_requests)

    # 3. Mount Versioned API
    app.include_router(api_v1_router, prefix="/api/v1")

    return app


app = create_app()
