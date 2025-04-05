from abc import ABC, abstractmethod
from .redis_client import redis_client
from typing import TypeVar, Generic, Any

T = TypeVar('T', )

class BaseRedis(ABC, Generic[T]):
    _client = redis_client

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