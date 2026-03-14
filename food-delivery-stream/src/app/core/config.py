from functools import lru_cache

from src.app.core.settings.cors import CORSSettings
from src.app.core.settings.db import DatabaseSettings
from src.app.core.settings.kafka import KafkaSettings
from src.app.core.settings.metadata import ProjectMetaData
from src.app.core.settings.otel import OTelSettings
from src.app.core.settings.redis import RedisSettings
from src.shared.logger.log_level import LogLevel


class Settings:
    """
    The Master Configuration Hub.

    This class now simply composes the self-initializing sub-settings.
    Since each sub-setting inherits from BaseAppConfig (with its own .env logic),
    this class doesn't even need to inherit from Pydantic's BaseSettings.
    """

    def __init__(self):
        # Every time these are initialized, they independently
        # look at the .env file and validate themselves.
        self.app: ProjectMetaData = ProjectMetaData()
        self.db: DatabaseSettings = DatabaseSettings()
        self.kafka: KafkaSettings = KafkaSettings()
        self.redis: RedisSettings = RedisSettings()
        self.otel: OTelSettings = OTelSettings()
        self.cors: CORSSettings = CORSSettings()

        self.LOG_LEVEL = LogLevel.INFO


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached instance of the Settings.
    Even though the sub-models read the .env, lru_cache ensures
    we only perform that initialization once.
    """
    return Settings()


# The global settings object used throughout the application
settings: Settings = get_settings()
