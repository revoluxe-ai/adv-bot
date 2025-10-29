from __future__ import annotations

from typing import Any, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:
    from .redis_client import RedisClient


@runtime_checkable
class BaseRedisManagerProtocol(Protocol):
    prefix: str

    def _get_key(
        self, *args: Any, **kwargs: Any
    ) -> str: ...  # instance method, aligns with BaseRedisManager

    @property
    def _client(self) -> "RedisClient": ...

    def _resolve_ttl(self, ttl: int | None = None) -> int | None: ...


if TYPE_CHECKING:
    from .base_redis_manager import BaseRedisManager
    from .redis_client import RedisClient
    from typing import cast

    class _Check(BaseRedisManager):
        prefix = "_"

        def _get_key(self, *args: Any, **kwargs: Any) -> str:
            return "dummy"

    def __accept_protocol(x: BaseRedisManagerProtocol) -> None: ...

    __accept_protocol(_Check(redis_client=cast(RedisClient, None)))
