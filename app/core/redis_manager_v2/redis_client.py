__all__ = ("RedisClient",)

from abc import ABC
from typing import Any, Union, cast
from collections.abc import Awaitable


from redis.asyncio import Redis


from dependency_injector.wiring import inject, Provide
from app.core.di.app_container import AppContainer


class RedisClient(ABC):
    @inject
    def __init__(self, redis_client: Redis = Provide[AppContainer.redis_client]) -> None:
        self._replica_read_client = redis_client
        self._replica_write_client = redis_client

    async def _maybe_await(self, value: Any) -> Any:
        """If value is awaitable, await it; otherwise return as-is."""
        if isinstance(value, Awaitable):
            return await value
        return value

    # @abstractmethod
    # def get_key(self, *args: Any, **kwargs: Any) -> str: ...

    # @property
    # @abstractmethod
    # def _prefix(self) -> str: ...

    # Методы для чтения (через реплику)
    async def get(self, key: str) -> bytes | None:
        return cast(Union[bytes, None], await self._maybe_await(self._replica_read_client.get(key)))

    async def mget(self, keys: list[str]) -> list[bytes | None]:
        return cast(list[Union[bytes, None]], await self._maybe_await(self._replica_read_client.mget(keys)))

    async def exists(self, key: str) -> int:
        return cast(int, await self._maybe_await(self._replica_read_client.exists(key)))

    async def keys(self, pattern: str = "*") -> list[str]:
        return cast(list[str], await self._maybe_await(self._replica_read_client.keys(pattern)))

    async def hget(self, name: str, key: str) -> bytes | None:
        return cast(Union[bytes, None], await self._maybe_await(self._replica_read_client.hget(name, key)))

    async def hgetall(self, name: str) -> dict[str, str]:
        return cast(dict[str, str], await self._maybe_await(self._replica_read_client.hgetall(name)))

    async def hmget(self, name: str, keys: list[str]) -> list[bytes | None]:
        return cast(list[Union[bytes, None]], await self._maybe_await(self._replica_read_client.hmget(name, keys)))

    async def hexists(self, name: str, key: str) -> bool:
        return cast(bool, await self._maybe_await(self._replica_read_client.hexists(name, key)))

    async def hkeys(self, name: str) -> list[str]:
        return cast(list[str], await self._maybe_await(self._replica_read_client.hkeys(name)))

    async def hvals(self, name: str) -> list[str]:
        return cast(list[str], await self._maybe_await(self._replica_read_client.hvals(name)))

    async def hlen(self, name: str) -> int:
        return cast(int, await self._maybe_await(self._replica_read_client.hlen(name)))

    async def llen(self, name: str) -> int:
        return cast(int, await self._maybe_await(self._replica_read_client.llen(name)))

    async def lindex(self, name: str, index: int) -> bytes | None:
        return cast(Union[bytes, None], await self._maybe_await(self._replica_read_client.lindex(name, index)))

    async def lrange(self, name: str, start: int, end: int) -> list[bytes]:
        return cast(list[bytes], await self._maybe_await(self._replica_read_client.lrange(name, start, end)))

    async def smembers(self, name: str) -> set[bytes]:
        return cast(set[bytes], await self._maybe_await(self._replica_read_client.smembers(name)))

    async def scard(self, name: str) -> int:
        return cast(int, await self._maybe_await(self._replica_read_client.scard(name)))

    async def sismember(self, name: str, value: str) -> bool:
        return cast(bool, await self._maybe_await(self._replica_read_client.sismember(name, value)))

    # Методы для записи (через мастер)
    async def set(self, key: str, value: str | bytes, ex: int | None = None) -> bool:
        return cast(bool, await self._maybe_await(self._replica_write_client.set(key, value, ex=ex)))

    async def mset(self, mapping: dict[str, str | bytes]) -> bool:
        return cast(bool, await self._maybe_await(self._replica_write_client.mset(mapping)))

    async def delete(self, *keys: str) -> int:
        return cast(int, await self._maybe_await(self._replica_write_client.delete(*keys)))

    async def expire(self, key: str, time: int) -> bool:
        return cast(bool, await self._maybe_await(self._replica_write_client.expire(key, time)))

    async def hset(self, name: str, key: str, value: str | bytes) -> int:
        return cast(int, await self._maybe_await(self._replica_write_client.hset(name, key, value)))  # type: ignore

    async def hdel(self, name: str, *keys: str) -> int:
        return cast(int, await self._maybe_await(self._replica_write_client.hdel(name, *keys)))  # type: ignore

    async def lpush(self, name: str, *values: str | bytes) -> int:
        return cast(int, await self._maybe_await(self._replica_write_client.lpush(name, *values)))

    async def rpush(self, name: str, *values: str | bytes) -> int:
        return cast(int, await self._maybe_await(self._replica_write_client.rpush(name, *values)))

    async def lpop(self, name: str) -> bytes | None:
        return cast(Union[bytes, None], await self._maybe_await(self._replica_write_client.lpop(name)))

    async def rpop(self, name: str) -> bytes | None:
        return cast(Union[bytes, None], await self._maybe_await(self._replica_write_client.rpop(name)))

    async def sadd(self, name: str, *values: str | bytes) -> int:
        return cast(int, await self._maybe_await(self._replica_write_client.sadd(name, *values)))

    async def srem(self, name: str, *values: str | bytes) -> int:
        return cast(int, await self._maybe_await(self._replica_write_client.srem(name, *values)))

    async def incr(self, name: str, amount: int = 1) -> int:
        return cast(int, await self._maybe_await(self._replica_write_client.incr(name, amount)))

    async def decr(self, name: str, amount: int = 1) -> int:
        return cast(int, await self._maybe_await(self._replica_write_client.decr(name, amount)))

    async def flushdb(self) -> bool:
        return cast(bool, await self._maybe_await(self._replica_write_client.flushdb()))

    # Исправленные методы Pipeline
    def read_pipeline(self) -> Any:
        """Создает pipeline для операций чтения"""
        return self._replica_read_client.pipeline()

    def write_pipeline(self) -> Any:
        """Создает pipeline для операций записи"""
        return self._replica_write_client.pipeline()

    async def execute_read_pipeline(self, commands: list[list[Any]]) -> list[Any]:
        """Выполняет список команд чтения через pipeline"""
        async with self._replica_read_client.pipeline() as pipe:
            for command in commands:
                cmd = command[0]
                args = command[1:]
                getattr(pipe, cmd)(*args)
            results = await pipe.execute()
        return cast(list[Any], results)

    async def execute_write_pipeline(self, commands: list[list[Any]]) -> list[Any]:
        """Выполняет список команд записи через pipeline"""
        async with self._replica_write_client.pipeline() as pipe:
            for command in commands:
                cmd = command[0]
                args = command[1:]
                getattr(pipe, cmd)(*args)
            results = await pipe.execute()
        return cast(list[Any], results)

    async def execute_pipeline_batch(
        self,
        read_commands: list[list[Any]] | None = None,
        write_commands: list[list[Any]] | None = None,
    ) -> dict[str, list[Any]]:
        """Выполняет пакет команд чтения и записи"""
        results = {}

        if read_commands:
            results["read"] = await self.execute_read_pipeline(read_commands)

        if write_commands:
            results["write"] = await self.execute_write_pipeline(write_commands)

        return results
