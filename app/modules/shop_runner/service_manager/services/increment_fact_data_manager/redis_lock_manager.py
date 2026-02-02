from __future__ import annotations

import logging
from typing import Final

from app.core.redis_manager_v2.redis_client import RedisClient

logger = logging.getLogger(__name__)


class RedisLockManager:
    _RELEASE_SCRIPT: Final[str] = (
        "if redis.call('get', KEYS[1]) == ARGV[1] then "
        "return redis.call('del', KEYS[1]) "
        "else "
        "return 0 "
        "end"
    )

    def __init__(self, redis_client: RedisClient) -> None:
        self._redis_client = redis_client

    async def acquire(self, key: str, value: str, ttl: int) -> bool:
        try:
            return await self._redis_client.set(key, value, ex=ttl, nx=True)
        except Exception as exc:  # pragma: no cover - guard unexpected errors
            logger.exception(
                "Redis lock acquire failed for key=%s ttl=%s", key, ttl, exc_info=exc
            )
            return False

    async def release(self, key: str, value: str) -> None:
        try:
            await self._redis_client.eval(self._RELEASE_SCRIPT, 1, key, value)
        except Exception as exc:  # pragma: no cover
            logger.exception(
                "Redis lock release failed for key=%s value=%s", key, value, exc_info=exc
            )
