from typing import Any
from typing import Protocol

from app.core.redis_manager_v2._redis_client import RedisClient


class BaseRedisManagerProtocol(Protocol):
    @property
    def _prefix(self) -> str: ...

    @property
    def _client(self) -> RedisClient: ...

    def _get_key(self, *args: Any, **kwargs: Any) -> str: ...
