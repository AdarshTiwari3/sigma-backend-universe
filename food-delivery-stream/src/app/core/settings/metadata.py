from enum import StrEnum

from src.app.core.settings.base import BaseAppConfig


class Environment(StrEnum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class ProjectMetaData(BaseAppConfig):
    """Project Metadata"""

    PROJECT_NAME: str = "FoodDeliveryStream"
    VERSION: str = "1.0.0"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    SERVICE_NAME: str = "order-stream-service"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

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
