from src.app.core.settings.base import BaseAppConfig


class CORSSettings(BaseAppConfig):
    """
    Configuration for Cross-Origin Resource Sharing (CORS).
    Attributes will be mapped from .env using 'CORS_' prefix.
    """

    # Defaults are provided, but will be overridden by .env
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]
    ALLOW_CREDENTIALS: bool = True
    ALLOW_METHODS: list[str] = ["*"]
    ALLOW_HEADERS: list[str] = ["*"]
