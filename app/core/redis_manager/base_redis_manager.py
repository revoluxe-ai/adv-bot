from abc import ABC

import redis

from .redis_client import redis_client


class BaseRedis(ABC):
    _client = redis_client

    @property
    def client(self) -> redis.asyncio.Redis:
        """Геттер для доступа к клиенту Redis"""
        return self._client

    # @abstractmethod
    # def _get_key(self, *args, **kwargs) -> str:
    #     pass
    #
    # @abstractmethod
    # async def get_one(self, *arg, **kwarg) -> T:
    #     pass

    # @abstractmethod
    # async def get_many(self, *args, **kwargs) -> list[T]:
    #     pass
    #

    # @abstractmethod
    # async def set_one(self, *arg: Any, **kwarg: Any):
    #     pass

    # @abstractmethod
    # async def set_many(self, objs: list[T], *arg, **kwarg):
    #     pass
