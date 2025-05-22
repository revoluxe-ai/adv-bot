from abc import ABC
from asyncio import Protocol

import redis

from .redis_client import redis_client


class BaseRedis(ABC):
    _client = redis_client

    @property
    def client(self) -> redis.asyncio.Redis:
        """Геттер для доступа к клиенту Redis"""
        return self._client


class BaseRedisProtocol(Protocol):
    _key: str = ...
    prefix: str = ...
    client: redis.asyncio.Redis
