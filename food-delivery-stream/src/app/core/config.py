from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.app.core.settings.base import BaseAppSettings
from src.app.core.settings.cors import CORSSettings
from src.app.core.settings.db import DatabaseSettings
from src.app.core.settings.kafka import KafkaSettings
from src.app.core.settings.otel import OTelSettings
from src.shared.logger.log_level import LogLevel


class Settings(BaseSettings):
    """
    The Master Configuration Hub.

    all sub-settings, this class provides a flat
    interface (e.g., settings.DB_USER) while keeping the logic
    physically separated in the /settings/ directory.
    """

    # Metadata stays at the top level
    app: BaseAppSettings = BaseAppSettings()

    # Infrastructure is composed
    db: DatabaseSettings = DatabaseSettings()
    kafka: KafkaSettings = KafkaSettings()
    otel: OTelSettings = OTelSettings()
    cors: CORSSettings = CORSSettings()

    # Global logger level
    LOG_LEVEL: LogLevel = LogLevel.INFO

    # Pydantic Configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_nested_delimiter="__",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached instance of the Settings.
    The @lru_cache ensures we only read the .env file once.
    """
    return Settings()


# The global settings object used throughout the application
settings = get_settings()
