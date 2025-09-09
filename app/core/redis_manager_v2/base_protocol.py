from typing import Protocol, Any


class BaseRedisManagerProtocol(Protocol):
    prefix: str

    def get_key(self, *args: Any, **kwargs: Any) -> str: ...
