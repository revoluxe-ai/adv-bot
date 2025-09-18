from abc import abstractmethod
from typing import Any

from dependency_injector.wiring import Provide, inject
from redis.asyncio import Redis

from app.core.di.app_container import AppContainer


class BaseRedisManager:
    prefix: str

    @inject
    def __init__(self, redis_client: Redis = Provide[AppContainer.redis_client]):
        self.__client = redis_client

    @abstractmethod
    def _get_key(self, *args: Any, **kwargs: Any) -> str: ...

    @property
    def _client(self) -> Redis:
        """Геттер для доступа к клиенту Redis"""
        return self.__client
