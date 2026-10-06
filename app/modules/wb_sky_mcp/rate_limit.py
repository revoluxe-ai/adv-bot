"""Счётчики лимитов в Redis. Недоступный Redis — отказ, без отдельной платформы."""

from __future__ import annotations

from app.modules.wb_sky_mcp.errors import McpError, McpStorageError
from app.modules.wb_sky_mcp.oauth_store import AsyncKv


class RedisRateLimiter:
    """Фиксированное окно на ключ Redis."""

    def __init__(self, redis: AsyncKv) -> None:
        self._redis = redis

    async def hit(self, bucket: str, identity: str, *, limit: int, window_seconds: int) -> None:
        """Увеличить счётчик. При превышении — ``RATE_LIMITED``.

        Raises:
            McpStorageError: Redis недоступен.
            McpError: лимит исчерпан.
        """
        key = f"mcp:rl:{bucket}:{identity}"
        try:
            count = await self._redis.incr(key)
            if count == 1:
                _ = await self._redis.expire(key, window_seconds)
        except Exception as exc:
            raise McpStorageError("redis unavailable") from exc
        if count > limit:
            raise McpError("RATE_LIMITED", "rate limit exceeded")
