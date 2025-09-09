from abc import abstractmethod
from typing import Any

from dependency_injector.wiring import inject, Provide
from redis.asyncio import Redis

from app.core.di.app_container import AppContainer


class BaseRedisManager:

    prefix: str

    @inject
    def __init__(self, redis_client: Redis = Provide[AppContainer.redis_client]):
        self._client = redis_client

    @property
    @abstractmethod
    def key(self, *args: Any, **kwargs: Any) -> str: ...
