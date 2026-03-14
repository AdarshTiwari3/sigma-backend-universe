"""
Structlog-based logging provider.

This module contains the concrete implementation of the ILogger interface
using the structlog library for structured logging and trace context injection.
"""

from typing import Any

import structlog

from src.shared.logger.context import TraceContext
from src.shared.logger.interface import ILogger
from src.shared.logger.log_level import LogLevel


class StructlogProvider(ILogger):
    """
    Concrete implementation of ILogger using structlog.

    Handles structured logging configuration, context propagation,
    and trace injection for distributed systems.
    """

    def __init__(self, is_dev: bool = False, log_level: LogLevel = LogLevel.INFO):
        """
        Initializes the Structlog engine.
        :param is_dev: If True, uses ConsoleRenderer (Pretty). If False, uses JSON.
        :param log_level: The minimum level to log (e.g., LogLevel.DEBUG).
        """
        self._is_dev = is_dev

        # 1. Pipeline: Order matters here!
        processors: list[Any] = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            self._inject_tracing_context,  # custom OTel injector
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ]

        # 2. Output selection based on environment
        if self._is_dev:
            processors.append(structlog.dev.ConsoleRenderer())
        else:
            processors.append(structlog.processors.JSONRenderer())

        # 3. Global Configuration (Only once!)
        if not structlog.is_configured():
            structlog.configure(
                processors=processors,
                logger_factory=structlog.PrintLoggerFactory(),
                # IMPORTANT: .value provides the integer (10, 20, etc.) structlog needs
                wrapper_class=structlog.make_filtering_bound_logger(log_level.value),
                cache_logger_on_first_use=True,
            )

        self._logger = structlog.get_logger()

    def _inject_tracing_context(
        self, _logger: Any, _name: str, event_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """Internal processor to stamp OTel IDs onto every log."""

        t_id = TraceContext.get_trace_id()
        s_id = TraceContext.get_span_id()

        # Standard OTel fields
        event_dict["trace_id"] = t_id
        event_dict["span_id"] = s_id

        return event_dict

    def log(self, level: LogLevel, message: str, **kwargs: Any) -> None:
        """Generic entry point using the Enum mapping."""
        method_name = LogLevel.to_str(level)
        method = getattr(self._logger, method_name)
        method(message, **kwargs)

    # --- Shorthand methods for better Developer Experience (DX) ---
    def debug(self, message: str, **kwargs: Any) -> None:
        """capture the debug"""
        self._logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """capture info"""
        self._logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """capture warning"""
        self._logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """capture error"""
        self._logger.error(message, **kwargs)

    def fatal(self, message: str, **kwargs: Any) -> None:
        """capture fatal/ critical things"""
        # We map our custom FATAL level to structlog's critical method
        self._logger.critical(message, **kwargs)

    def bind(self, **kwargs: Any) -> None:
        """Contextual binding for subsequent logs in the same context/thread."""
        structlog.contextvars.bind_contextvars(**kwargs)
