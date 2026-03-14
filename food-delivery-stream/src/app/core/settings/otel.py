from src.app.core.settings.base import BaseAppConfig


class OTelSettings(BaseAppConfig):
    """Configuration for OpenTelemetry and Distributed Tracing."""

    OTEL_SERVICE_NAME: str = "order-stream-service"
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = "http://localhost:4317"
