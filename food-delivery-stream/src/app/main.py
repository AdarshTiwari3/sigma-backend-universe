import time
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response

# --- Open Telemetry Imports ----
from opentelemetry import propagate, trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from src.app.core.config import settings
from src.app.infrastructure.database.session import engine
from src.app.infrastructure.kafka.producer import get_kafka_producer, init_kafka_producer
from src.shared.logger import get_logger

logger = get_logger()


def setup_tracing(fastapi_app: FastAPI) -> None:
    """
    Configures OpenTelemetry with conditional exporting.
    Ensures observability matches the environment.
    """

    resource = Resource.create(
        attributes={
            SERVICE_NAME: settings.SERVICE_NAME,
            "env": settings.ENVIRONMENT,
        }
    )

    provider = TracerProvider(resource=resource)

    # --- Conditional Exporter Logic ---
    if settings.ENVIRONMENT == "development":
        # Local: Simple console output for debugging
        processor = BatchSpanProcessor(ConsoleSpanExporter())
        logger.info("otel_tracing_configured", exporter="console")

    else:
        # Prod/Staging: High-performance gRPC export to Jaeger/Tempo
        # settings.OTLP_ENDPOINT should be something like "http://jaeger:4317"
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True
        )
        processor = BatchSpanProcessor(otlp_exporter)
        logger.info(
            "otel_tracing_configured",
            exporter="otlp",
        )
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # This ensures inject(headers) actually works for Kafka/External calls
    propagate.set_global_textmap(TraceContextTextMapPropagator())

    # ---- Instrument SQLAlchemy ---
    # It will automatically detect your engine and trace all queries
    SQLAlchemyInstrumentor().instrument(
        engine=engine.sync_engine,  # For async engines, we instrument the underlying sync_engine
        service_name=settings.SERVICE_NAME,
    )

    # Automatically trace FastAPI requests/responses
    FastAPIInstrumentor.instrument_app(fastapi_app)


@asynccontextmanager
async def lifespan(_fastapi_app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manages the application lifecycle.
    Ensures infrastructure (Kafka, DB) starts and stops gracefully.
    """
    # --- Startup Logic ---
    logger.info(
        "services_starting",
        project=settings.PROJECT_NAME,
        service=settings.SERVICE_NAME,
        version=settings.VERSION,
        env=settings.ENVIRONMENT,
        kafka_broker=settings.KAFKA_BOOTSTRAP_SERVERS,
        db_host=settings.DB_HOST,
    )

    # 1. Initialize Kafka Producer
    try:
        init_kafka_producer()
        logger.info("kafka_producer_ready")
    except Exception as e:
        logger.error("kafka_initialization_failed", error=str(e))
        raise e

    yield

    # --- Shutdown Logic ---
    logger.info("services_shutting_down_initiated")

    # 1. Flush Kafka buffer
    try:
        # FIX: Access the instance via the getter function
        producer = get_kafka_producer()
        logger.info("flushing_kafka_producer_buffer")

        unfilled_messages = producer.flush(timeout=10.0)

        if unfilled_messages > 0:
            logger.warning("kafka_flush_incomplete", missing_count=unfilled_messages)
        else:
            logger.info("kafka_flush_successful")
    except Exception as e:
        logger.error("kafka_shutdown_error", error=str(e))

    # 2. Close Database connection pools
    try:
        logger.info("closing_database_connection_pool")
        # dispose() is the correct way to close all underlying connections in the pool
        await engine.dispose()
        logger.info("database_connections_closed")
    except Exception as e:
        logger.error("database_shutdown_error", error=str(e))

    logger.info("cleanup_complete_safe_to_exit")


app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, lifespan=lifespan)

# Initialize Tracing BEFORE middleware/routes
setup_tracing(app)


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
