"""Log Level implementation"""

from enum import IntEnum


class LogLevel(IntEnum):
    """Enumeration representing supported log levels."""

    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    FATAL = 50

    @classmethod
    def to_str(cls, level: int) -> str:
        """Converts integer level back to lowercase string for Structlog/JSON."""
        mapping: dict[LogLevel, str] = {
            cls.DEBUG: "debug",
            cls.INFO: "info",
            cls.WARNING: "warning",
            cls.ERROR: "error",
            cls.FATAL: "fatal",
        }
        return mapping.get(LogLevel(level), "info")
