__all__ = ("_RedisLifecycle", "create_redis_client")

from dependency_injector import resources
from redis.asyncio import Redis

from app.configs.infrastructure_config.redis_config import RedisConfig


def create_redis_client(redis_config: RedisConfig) -> Redis:
    """Синхронно создаёт Redis asyncio-клиент. Проверка доступности и закрытие
    выполняются в приватном lifecycle-ресурсе.
    """
    client = Redis[str, str](
        host=redis_config.host,
        port=redis_config.port,
        db=redis_config.db,
        password=redis_config.password,
    )
    return client


class _RedisLifecycle(resources.AsyncResource[None]):
    async def init(self, client: Redis) -> None:
        try:
            await client.ping()
        except Exception:
            await client.aclose()
            raise

    async def shutdown(self, client: Redis | None = None) -> None:
        if client:
            await client.aclose()
