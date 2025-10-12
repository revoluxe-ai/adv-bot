from abc import abstractmethod, ABC
from typing import Any, Optional

import typing

if typing.TYPE_CHECKING:
    from app.core.redis_manager_v2.redis_client import RedisClient


class BaseRedisManager(ABC):
    prefix: str
    default_ttl: Optional[int] = None

    def __init__(self, redis_client: "RedisClient", ttl: Optional[int] = None) -> None:
        self.__client = redis_client
        self._ttl: Optional[int] = ttl if ttl is not None else self.default_ttl

    @abstractmethod
    def _get_key(self, *args: Any, **kwargs: Any) -> str: ...

    @property
    def _client(self) -> "RedisClient":
        """Геттер для доступа к клиенту Redis"""
        return self.__client

    def _resolve_ttl(self, ttl: int | None = None) -> int | None:
        """Определяет итоговый TTL для ключа Redis.
        Возвращает None, если ни аргумент, ни self._ttl не заданы (без истечения).
        """
        if ttl is not None:
            return ttl
        if self._ttl is not None:
            return self._ttl
        return None
