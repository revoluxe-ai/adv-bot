from asyncio import Protocol
from abc import abstractmethod

import redis

from .redis_client import redis_client


class BaseRedis:
    _client = redis_client

    @property
    def client(self) -> redis.asyncio.Redis:
        """Геттер для доступа к клиенту Redis"""
        return self._client


class BaseRedisProtocol(Protocol):
    @property
    @abstractmethod
    def _key(self) -> str:
        pass
    prefix: str
    client: redis.asyncio.Redis
