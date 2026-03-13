from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.api.middleware.logging import log_requests
from src.app.api.v1.router import api_v1_router
from src.app.core.config import settings
from src.app.core.lifespan import lifespan
from src.app.core.tracing import setup_tracing


def create_app() -> FastAPI:

    app = FastAPI(
        title=settings.app.PROJECT_NAME,
        version=settings.app.VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    # 1. Setup Observability/Tracing
    setup_tracing(app)

    # Register CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.ALLOWED_ORIGINS,
        allow_credentials=settings.cors.ALLOW_CREDENTIALS,
        allow_methods=settings.cors.ALLOW_METHODS,
        allow_headers=settings.cors.ALLOW_HEADERS,
    )

    # 2. Register Middleware
    app.middleware("http")(log_requests)

    # 3. Mount Versioned API
    app.include_router(api_v1_router, prefix="/api/v1")

    return app


app = create_app()
