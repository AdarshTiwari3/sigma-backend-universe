from enum import StrEnum
from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.shared.logger.log_level import LogLevel


class Environment(StrEnum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.

    Supports loading from:
    - .env file (development)
    - system environment variables (production)
    """

    # --- Project Metadata ---
    PROJECT_NAME: str = "FoodDeliveryStream"
    VERSION: str = "1.0.0"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    SERVICE_NAME: str = "order-stream-service"

    # --- Logger Configuration ---
    # This feeds directly into our StructlogProvider
    LOG_LEVEL: LogLevel = LogLevel.INFO

    # --- Kafka Configuration ---
    # These match your Docker Compose setup for the Order Service
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_ORDER_TOPIC: str = "order-events"
    KAFKA_CLIENT_ID: str = "order-service-producer"

    # --- OTel Configuration ---
    OTEL_SERVICE_NAME: str = "order-stream-service"
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = "http://localhost:4317"

    # --- Database Configuration ---
    DB_USER: str = "postgres"
    DB_PASSWORD: SecretStr = SecretStr("postgres")
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "food_delivery_db"

    # --- Database Configuration for Production ---
    DATABASE_URL: str | None = None

    # --- Pydantic Settings Config ---
    # This tells Pydantic to look for a .env file first
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        # 3. Add this to prevent crashes if .env has extra keys
        extra="ignore",
    )

    @property
    def is_dev(self) -> bool:
        """Helper to check if we are in development mode."""
        return self.ENVIRONMENT == Environment.DEVELOPMENT

    @property
    def is_prod(self) -> bool:
        """Check if running in production."""
        return self.ENVIRONMENT == Environment.PRODUCTION

    @property
    def is_test(self) -> bool:
        """Check if running in test environment."""
        return self.ENVIRONMENT == Environment.TESTING

    @property
    def debug(self) -> bool:
        """Enable debug mode automatically in development."""
        return self.is_dev

    # We use a computed property for the DSN (Data Source Name)
    @property
    def database_url(self) -> str:
        """Constructs the SQLAlchemy connection string."""
        if self.DATABASE_URL:
            return self.DATABASE_URL

        password = self.DB_PASSWORD.get_secret_value()
        return f"postgresql+asyncpg://{self.DB_USER}:{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


# -----------------------------
# Cached Settings Instance
# -----------------------------
@lru_cache
def get_settings() -> Settings:
    """
    Returns cached settings instance.

    Prevents reloading env variables multiple times.
    """
    return Settings()


# Global settings object
settings = get_settings()
