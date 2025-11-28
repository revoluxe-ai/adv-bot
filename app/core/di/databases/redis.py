"""Модуль для работы с Redis через DI."""

__all__ = ("RedisLifecycle", "create_redis_client")

from dependency_injector import resources
from redis.asyncio import Redis

from app.configs import AppConfig


def create_redis_client(app_config: AppConfig) -> Redis:  # pyright: ignore
    """Синхронно создаёт Redis asyncio-клиент.
    Проверка доступности и закрытие выполняются в приватном lifecycle-ресурсе.
    """
    redis_config = app_config.infrastructure.redis
    client = Redis(
        host=redis_config.host,
        port=redis_config.port,
        db=redis_config.db,
        password=redis_config.password,
        decode_responses=True,
    )
    return client


class RedisLifecycle(resources.AsyncResource[Redis]):  # pyright: ignore
    async def init(self, client: Redis) -> None:  # pyright: ignore
        try:
            await client.ping() # pyright: ignore
        except Exception as exc:
            await client.aclose()  # type: ignore[attr-defined]
            raise exc

    async def shutdown(self, client: Redis | None = None) -> None:  # pyright: ignore
        if client:
            await client.aclose()  # type: ignore[attr-defined]
