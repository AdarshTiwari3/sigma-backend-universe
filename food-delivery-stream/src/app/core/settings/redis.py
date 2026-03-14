from pydantic import computed_field
from pydantic_settings import SettingsConfigDict

from src.app.core.settings.base import BaseAppConfig


class RedisSettings(BaseAppConfig):
    """
    Configuration for Standalone Redis.

    Mapping Strategy:
    In main Settings class, this will be assigned to an attribute named 'redis'.
    Pydantic will look for environment variables prefixed with 'REDIS_'.
    Example: REDIS_HOST -> self.HOST
    """

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    HOST: str = "localhost"
    PORT: int = 6379
    DB: int = 0
    PASSWORD: str | None = None

    # --- Connection Pool Management ---
    # In a high-concurrency 'FoodDeliveryStream', pooling is critical
    # to avoid the overhead of opening/closing TCP connections.
    MAX_CONNECTIONS: int = 10

    # --- Developer Experience ---
    # Automatically convert bytes to strings so you don't have to .decode()
    DECODE_RESPONSES: bool = True

    # --- Timeouts (Crucial for System Design) ---
    # How long to wait for a connection before failing
    SOCKET_TIMEOUT: float = 5.0
    # How long to wait for a response before failing
    SOCKET_CONNECT_TIMEOUT: float = 5.0

    @computed_field  # behaves like read only
    @property
    def DSN(self) -> str:
        """Constructs the redis connection string. Data Source Name"""
        auth = f":{self.PASSWORD}@" if self.PASSWORD else ""
        return f"redis://{auth}{self.HOST}:{self.PORT}/{self.DB}"
