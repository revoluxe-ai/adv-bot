import logging
from typing import cast

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

redis_manaeger = None


class RedisManager:
    _instance = None
    _redis_conn = None

    def __new__(cls) -> "RedisManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def get_connection(self) -> Redis:
        if self._redis_conn is None:
            self._redis_conn = cast(Redis, await Redis.from_url("redis://localhost/0"))
        return self._redis_conn
