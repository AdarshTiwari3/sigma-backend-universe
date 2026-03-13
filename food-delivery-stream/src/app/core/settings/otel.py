from pydantic_settings import BaseSettings


class OTelSettings(BaseSettings):
    """Configuration for OpenTelemetry and Distributed Tracing."""

    OTEL_SERVICE_NAME: str = "order-stream-service"
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = "http://localhost:4317"
