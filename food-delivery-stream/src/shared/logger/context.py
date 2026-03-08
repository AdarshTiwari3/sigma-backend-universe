"""Utilities for extracting OpenTelemetry trace and span IDs for log correlation."""

from opentelemetry import trace


class TraceContext:
    """
    Utility class to extract OpenTelemetry identifiers for log correlation.
    Follows PBC standards for distributed tracing.
    """

    @staticmethod
    def get_trace_id() -> str:
        """Retrieves the Hex Trace ID from the current active span."""
        span = trace.get_current_span()
        context = span.get_span_context()

        if context.is_valid:
            # 032x ensures 32-char hex padding for Trace ID
            return format(context.trace_id, "032x")

        return "n/a"

    @staticmethod
    def get_span_id() -> str:
        """Retrieves the Hex Span ID from the current active span."""
        span = trace.get_current_span()
        context = span.get_span_context()

        if context.is_valid:
            # 016x ensures 16-char hex padding for Span ID
            return format(context.span_id, "016x")
        return "n/a"
