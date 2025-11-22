import os
from abc import ABC, abstractmethod
import typing

import redis
from dependency_injector.wiring import inject, Provide

from app.core.redis_manager_v2.redis_client import RedisClient

redis_host = os.environ.get("REDIS_HOST")
assert redis_host is not None, "REDIS_HOST environment variable not set"


class RedisCacheBase(ABC):
    _prefix: str

    def __init__(self, decode_bytes: bool = True) -> None:
        self._decode_bytes = decode_bytes

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

    @inject
    def __get_client(
        self, client: RedisClient = Provide["redis_client_wrapper"]
    ) -> RedisClient:  # noqa
        return client

    @property
    def client(self) -> RedisClient:
        return self.__get_client()

    @property
    def _client(self) -> RedisClient:
        return self.client

    @property
    def key(self) -> str:
        return self._key
