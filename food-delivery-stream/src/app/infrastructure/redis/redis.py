from redis import asyncio as redis
from redis.backoff import FullJitterBackoff
from redis.exceptions import BusyLoadingError, ConnectionError, TimeoutError
from redis.retry import Retry

from src.app.core.config import settings
from src.shared.logger import get_logger

logger = get_logger()


class RedisManager:
    def __init__(self):
        self._client: redis.Redis | None = None
        self._pool: redis.ConnectionPool | None = None

    async def connect(self):
        if self._client is not None:
            return

        logger.info("Initializing Redis connection pool...", host=settings.redis.HOST)

        # Exponential Backoff + Jitter
        # 'base' is the initial wait (1s)
        # 'cap' is the maximum wait (10s) to prevent infinite waiting
        # The library's ExponentialBackoff naturally applies randomness (Jitter)
        backoff = FullJitterBackoff(base=1, cap=10)

        # We retry 3 times before giving up
        retry_strategy = Retry(backoff, 3)
        try:
            self._pool = redis.ConnectionPool.from_url(
                url=settings.redis.DSN,
                max_connections=settings.redis.MAX_CONNECTIONS,
                decode_responses=settings.redis.DECODE_RESPONSES,
                socket_timeout=settings.redis.SOCKET_TIMEOUT,
                socket_connect_timeout=settings.redis.SOCKET_CONNECT_TIMEOUT,
                retry=retry_strategy,
                retry_on_error=[ConnectionError, TimeoutError, BusyLoadingError],
                health_check_interval=30,  # Built-in background ping every 30s
            )
            self._client: redis.Redis = redis.Redis(connection_pool=self._pool)

            # Initial pulse check

            await self._client.ping()
            logger.info("Redis connected successfully.")

        except redis.RedisError as e:
            logger.error(
                "Critical: Redis connection failed after retries", error=str(e), exception=e
            )
            self._client = None
            raise e

    async def check_health(self) -> bool:
        """Exposes a boolean check for monitoring tools."""
        try:
            if self._client:
                return await self._client.ping()
            return False
        except Exception:
            return False

    async def disconnect(self):
        """Gracefully shutdown the Redis connection."""

        if self._client:
            await self._client.aclose()
            logger.info("Redis connection closed.")
            self._client = None
            self._pool = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            raise RuntimeError("RedisManager is not connected. Call connect() first.")
        return self._client


redis_manager = RedisManager()
