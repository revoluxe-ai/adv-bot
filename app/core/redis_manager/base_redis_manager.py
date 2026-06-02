from __future__ import annotations

from asyncio import Protocol
from typing import TYPE_CHECKING

import redis

if TYPE_CHECKING:
    from redis.asyncio.client import Redis as AsyncRedis

from .redis_client import redis_client


class BaseRedis:
    _client = redis_client

    @property
    def client(self) -> AsyncRedis[bytes]:
        """Геттер для доступа к клиенту Redis"""
        return self._client


class BaseRedisProtocol(Protocol):
    _key: str
    prefix: str
    client: AsyncRedis[bytes]
