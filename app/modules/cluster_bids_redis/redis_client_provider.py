"""Direct Redis client creation from config for cluster bids (no DI context)."""

from __future__ import annotations

from app.configs import AppConfig
from app.core.di.databases.redis import create_redis_client
from app.core.redis_manager_v2.redis_client import RedisClient

_client: RedisClient | None = None

# TODO: Вынести в DI
def get_redis_client() -> RedisClient:
    """
    Return a shared RedisClient (lazy singleton).

    Use when DI context (WBManagerHub, etc.) is not available,
    e.g. in CalculatedKeywordsManager running from bot/phrases_processor.
    Reuses one connection pool to avoid exhaustion under load.
    """
    global _client
    if _client is None:
        config = AppConfig.create()
        raw = create_redis_client(config)
        _client = RedisClient(redis_client=raw)
    return _client
