import os
from abc import ABC, abstractmethod
import typing

import redis

redis_host = os.environ.get("REDIS_HOST")
assert redis_host is not None, "REDIS_HOST environment variable not set"

redis_client = redis.asyncio.Redis(host=redis_host, port=6379, db=0)


class RedisCacheBase(ABC):
    _prefix: str
    _client: redis.asyncio.Redis = redis_client

    @property
    @abstractmethod
    def _unique_id(self: typing.Any) -> str:
        pass

    def __init_subclass__(cls, prefix: str, **kwargs: typing.Any) -> None:
        cls._prefix = prefix
        kwargs.pop("prefix", None)
        super().__init_subclass__(**kwargs)

    @property
    def _key(self) -> str:
        return f"{self._prefix}:{self._unique_id}"

    @property
    def client(self) -> redis.asyncio.Redis:
        return self._client

    @property
    def key(self) -> str:
        return self._key
