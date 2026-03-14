from pydantic import SecretStr, computed_field

from src.app.core.settings.base import BaseAppConfig


class DatabaseSettings(BaseAppConfig):
    """Database configuation"""

    DB_USER: str = "postgres"
    DB_PASSWORD: SecretStr = SecretStr("password")
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "food_delivery_db"
    DATABASE_URL: str | None = None

    @computed_field
    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        password = self.DB_PASSWORD.get_secret_value()
        return f"postgresql+asyncpg://{self.DB_USER}:{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
