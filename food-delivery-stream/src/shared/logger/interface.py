from abc import ABC, abstractmethod
from typing import Any

from src.shared.logger.log_level import LogLevel


class ILogger(ABC):
    @abstractmethod
    def log(self, level: LogLevel, message: str, **kwargs: Any) -> None:
        pass

    @abstractmethod
    def info(self, message: str, **kwargs: Any) -> None:
        pass

    @abstractmethod
    def error(self, message: str, **kwargs: Any) -> None:
        pass

    @abstractmethod
    def debug(self, message: str, **kwargs: Any) -> None:
        pass

    @abstractmethod
    def warning(self, message: str, **kwargs: Any) -> None:
        pass

    @abstractmethod
    def bind(self, **kwargs: Any) -> None:
        pass
