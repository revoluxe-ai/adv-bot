"""Redis клиент для error-collector."""

import logging

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

# Типизация Redis в redis-py/typing может отличаться от рантайма,
# поэтому держим Any-совместимую аннотацию (важнее стабильный рантайм).
_redis_client = None


async def get_redis_client(host: str, port: int, password: str | None = None):
    """Получает или создает Redis клиент."""
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis(
            host=host,
            port=port,
            password=password,
            db=0,
            decode_responses=True,
        )
        logger.info("Created Redis client: %s:%d", host, port)
    return _redis_client

