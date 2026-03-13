from pydantic import SecretStr
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuation"""

    DB_USER: str = "postgres"
    DB_PASSWORD: SecretStr = SecretStr("postgres")
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "food_delivery_db"
    DATABASE_URL: str | None = None

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        password = self.DB_PASSWORD.get_secret_value()
        return f"postgresql+asyncpg://{self.DB_USER}:{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
