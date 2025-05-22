import os
from abc import ABC

import redis
from mypy.semanal_shared import abstractmethod

redis_host = os.environ.get("REDIS_HOST")


redis_client = redis.asyncio.Redis(host=redis_host, port=6379, db=0)


class RedisCacheBase(ABC):
    _prefix: str
    _client: redis.asyncio.Redis = redis_client

    @property
    @abstractmethod
    def _unique_id(self) -> str:
        pass

    def __init_subclass__(cls, prefix: str, **kwargs) -> None:
        cls._prefix = prefix
        super().__init_subclass__(**kwargs)

    @property
    def _key(self) -> str:
        return f"{self._prefix}:{self._unique_id}"
