from fastapi import FastAPI
from opentelemetry import propagate, trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.confluent_kafka import ConfluentKafkaInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from src.app.core.config import settings
from src.app.infrastructure.database.session import engine
from src.shared.logger import get_logger

logger = get_logger()


def setup_tracing(fastapi_app: FastAPI) -> None:
    """
    Configures OpenTelemetry with conditional exporting.
    Ensures observability matches the environment.
    """
    try:
        resource = Resource.create(
            attributes={
                SERVICE_NAME: settings.app.SERVICE_NAME,
                "env": settings.app.ENVIRONMENT,
            }
        )

        provider = TracerProvider(resource=resource)

        # --- Conditional Exporter Logic ---
        if settings.app.is_dev:
            # Local: Simple console output for debugging
            processor = BatchSpanProcessor(ConsoleSpanExporter())
            logger.info("otel_tracing_configured", exporter="console")

        else:
            # Prod/Staging: High-performance gRPC export to Jaeger/Tempo
            # settings.otel.OTLP_ENDPOINT should be something like "http://jaeger:4317"
            otlp_exporter = OTLPSpanExporter(
                endpoint=settings.otel.OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True
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

        # Instrument Redis
        # This will catch all calls made via your RedisManager's client

        RedisInstrumentor().instrument()

        # Instrument Kafka
        # This tracks the 'produce' calls and handles the trace propagation automatically
        ConfluentKafkaInstrumentor().instrument()

        # ---- Instrument SQLAlchemy ---
        # It will automatically detect your engine and trace all queries
        SQLAlchemyInstrumentor().instrument(
            engine=engine.sync_engine,  # For async engines, we instrument the underlying sync_engine
            service_name=settings.app.SERVICE_NAME,
        )

        # Automatically trace FastAPI requests/responses
        FastAPIInstrumentor.instrument_app(fastapi_app)

    except Exception as e:
        logger.error("otel_setup_failed", error=str(e))
