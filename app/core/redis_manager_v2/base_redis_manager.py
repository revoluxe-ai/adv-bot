from abc import abstractmethod, ABC
from typing import Any

from ._redis_client import RedisClient
from .base_redis_manager_protocol import BaseRedisManagerProtocol


class BaseRedisManager(ABC, BaseRedisManagerProtocol):
    def __init__(self):
        redis_client = RedisClient()
        self.__redis_client = redis_client

    @abstractmethod
    def _get_key(self, *args: Any, **kwargs: Any) -> str:
        pass

    @property
    @abstractmethod
    def _prefix(self) -> str:
        pass

    @property
    def _client(self) -> RedisClient:
        """Геттер для доступа к клиенту Redis"""
        return self.__redis_client
