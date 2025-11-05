__all__ = ("RedisClient",)

import asyncio
from typing import Any, cast
from collections.abc import Mapping
from typing import TypeVar
from collections.abc import Awaitable
from redis.asyncio import Redis
from redis.asyncio.client import Pipeline

T = TypeVar("T")

# TODO: Внедрить проверку на циклические импорты


# TODO: Сделать, чтобы парсер обновлял только РК, где started и включена Аукцион


# TODO Сделать HELM-chart


#  TODO Сделать отправку ошибок  из кубера в телегу
# TODO: Инспектор Pycharm пишет, что cast-ы здесь не нужны, пока просто отключил инспецию, оставил только синтаксис

def ensure_awaitable(obj: Awaitable[T] | T) -> Awaitable[T]:
    if hasattr(obj, "__await__"):
        return obj
    return asyncio.sleep(0, result=obj)

# TODO: Чтобы быстрее закинуть в прод убрал ABC из класса RedisClient
class RedisClient:
    def __init__(self, redis_client: Redis) -> None:
        self._replica_read_client = redis_client
        self._replica_write_client = redis_client

    # Методы для чтения (через реплику)
    async def get(self, key: str) -> bytes | None:
        return cast(
            bytes | None, await ensure_awaitable(self._replica_read_client.get(key))
        )

    async def mget(self, keys: list[str]) -> list[bytes | None]:
        return cast(
            list[bytes | None],
            await ensure_awaitable(self._replica_read_client.mget(keys)),
        )

    async def exists(self, key: str) -> int:
        return cast(int, await ensure_awaitable(self._replica_read_client.exists(key)))

    async def keys(self, pattern: str = "*") -> list[str]:
        return cast(
            list[str], await ensure_awaitable(self._replica_read_client.keys(pattern))
        )

    async def hget(self, name: str, key: str) -> bytes | None:
        return cast(
            bytes | None,
            await ensure_awaitable(self._replica_read_client.hget(name, key)),
        )

    async def hgetall(self, name: str) -> dict[str, str]:
        return cast(
            dict[str, str],
            await ensure_awaitable(self._replica_read_client.hgetall(name)),
        )

    async def hmget(self, name: str, keys: list[str]) -> list[bytes | None]:
        return cast(
            list[bytes | None],
            await ensure_awaitable(self._replica_read_client.hmget(name, keys)),
        )

    async def hexists(self, name: str, key: str) -> bool:
        return cast(
            bool, await ensure_awaitable(self._replica_read_client.hexists(name, key))
        )

    async def hkeys(self, name: str) -> list[str]:
        return cast(
            list[str], await ensure_awaitable(self._replica_read_client.hkeys(name))
        )

    async def hvals(self, name: str) -> list[str]:
        return cast(
            list[str], await ensure_awaitable(self._replica_read_client.hvals(name))
        )

    async def hlen(self, name: str) -> int:
        return cast(int, await ensure_awaitable(self._replica_read_client.hlen(name)))

    async def llen(self, name: str) -> int:
        return cast(int, await ensure_awaitable(self._replica_read_client.llen(name)))

    async def lindex(self, name: str, index: int) -> bytes | None:
        return cast(
            bytes | None,
            await ensure_awaitable(self._replica_read_client.lindex(name, index)),
        )

    async def lrange(self, name: str, start: int, end: int) -> list[bytes]:
        return cast(
            list[bytes],
            await ensure_awaitable(self._replica_read_client.lrange(name, start, end)),
        )

    async def smembers(self, name: str) -> set[bytes]:
        return cast(
            set[bytes], await ensure_awaitable(self._replica_read_client.smembers(name))
        )

    async def srem(self, name: str, *values: str | bytes) -> int:
        return cast(
            int, await ensure_awaitable(self._replica_write_client.srem(name, *values))
        )

    async def scard(self, name: str) -> int:
        return cast(int, await ensure_awaitable(self._replica_read_client.scard(name)))

    async def sismember(self, name: str, value: str) -> bool:
        return cast(
            bool,
            await ensure_awaitable(self._replica_read_client.sismember(name, value)),
        )

    # Методы для записи (через мастер)
    async def set(
        self,
        key: str,
        value: str | bytes,
        ex: int | None = None,
        px: int | None = None,
    ) -> bool:
        return cast(
            bool,
            await ensure_awaitable(
                self._replica_write_client.set(key, value, ex=ex, px=px)
            ),
        )

    async def set_if_not_exists(
        self, key: str, value: str | bytes, ex: int | None = None, px: int | None = None
    ) -> bool:
        """Set key only if it does not exist (NX). Returns True if set, False otherwise."""
        return bool(
            await ensure_awaitable(
                self._replica_write_client.set(key, value, ex=ex, px=px, nx=True)
            )
        )

    async def mset(self, mapping: Mapping[str, Any]) -> bool:
        return cast(
            bool, await ensure_awaitable(self._replica_write_client.mset(mapping))
        )

    async def delete(self, *keys: str) -> int:
        return cast(
            int, await ensure_awaitable(self._replica_write_client.delete(*keys))
        )

    async def expire(self, key: str, time: int) -> bool:
        return cast(
            bool, await ensure_awaitable(self._replica_write_client.expire(key, time))
        )

    async def pexpire(self, key: str, time_ms: int) -> bool | None:
        result =  await ensure_awaitable(self._replica_write_client.pexpire(key, time_ms))
        if isinstance(result, int):
            if result == 1:
                return True
            else:
                return False
        else:
            return None



    async def ttl(self, key: str) -> int:
        return cast(int, await ensure_awaitable(self._replica_read_client.ttl(key)))

    async def pttl(self, key: str) -> int:
        return cast(int, await ensure_awaitable(self._replica_read_client.pttl(key)))

    async def hset(self, name: str, key: str, value: str | bytes) -> int:
        if isinstance(value, bytes):
            safe_val: str = value.decode("utf-8", "ignore")
        else:
            safe_val = value
        return cast(
            int,
            await ensure_awaitable(
                self._replica_write_client.hset(name, key, safe_val)
            ),
        )

    async def hdel(self, name: str, *keys: str) -> int:
        return cast(
            int, await ensure_awaitable(self._replica_write_client.hdel(name, *keys))
        )

    async def lpush(self, name: str, *values: str | bytes) -> int:
        return cast(
            int, await ensure_awaitable(self._replica_write_client.lpush(name, *values))
        )

    async def rpush(self, name: str, *values: str | bytes) -> int:
        return cast(
            int, await ensure_awaitable(self._replica_write_client.rpush(name, *values))
        )

    async def lpop(self, name: str) -> bytes | None:
        return cast(
            bytes | None, await ensure_awaitable(self._replica_write_client.lpop(name))
        )

    async def rpop(self, name: str) -> bytes | None:
        return cast(
            bytes | None, await ensure_awaitable(self._replica_write_client.rpop(name))
        )

    async def sadd(self, name: str, *values: str | bytes) -> int:
        return cast(
            int, await ensure_awaitable(self._replica_write_client.sadd(name, *values))
        )

    async def incr(self, name: str, amount: int = 1) -> int:
        return cast(
            int, await ensure_awaitable(self._replica_write_client.incr(name, amount))
        )

    async def decr(self, name: str, amount: int = 1) -> int:
        return cast(
            int, await ensure_awaitable(self._replica_write_client.decr(name, amount))
        )

    async def flushdb(self) -> bool:
        return cast(bool, await ensure_awaitable(self._replica_write_client.flushdb()))

    def read_pipeline(self) -> Pipeline:
        """Создает pipeline для операций чтения"""
        return self._replica_read_client.pipeline()

    def write_pipeline(self) -> Pipeline:  # добавлена аннотация возвращаемого типа
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
        results: dict[str, list[Any]] = {}

        if read_commands:
            results["read"] = await self.execute_read_pipeline(read_commands)

        if write_commands:
            results["write"] = await self.execute_write_pipeline(write_commands)

        return results

    async def eval(
        self,
        script: str,
        numkeys: int,
        *keys_and_args: str | bytes | int,
    ) -> Any:
        """Execute a Lua script on the Redis server"""
        return await ensure_awaitable(
            self._replica_write_client.eval(script, numkeys, *keys_and_args)
        )
