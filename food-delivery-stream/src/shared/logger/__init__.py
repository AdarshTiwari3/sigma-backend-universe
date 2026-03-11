"""Application logging utilities and logger factory."""

from functools import lru_cache

from src.shared.logger.interface import ILogger
from src.shared.logger.log_level import LogLevel
from src.shared.logger.provider.structlog_provider import StructlogProvider


@lru_cache
def get_logger() -> ILogger:
    """
    Factory function that returns the application's logger instance.

    The function is decorated with `lru_cache` to ensure that the logger
    is created only once (singleton behavior). Subsequent calls return
    the same cached instance, preventing multiple logger initializations.
    """
    # pylint: disable=import-outside-toplevel
    from src.app.core.config import settings

    return StructlogProvider(
        is_dev=settings.is_dev,
        log_level=settings.LOG_LEVEL,
    )


# logger = get_logger() # import this in main to avoid circular imports

__all__ = ["LogLevel", "ILogger"]
