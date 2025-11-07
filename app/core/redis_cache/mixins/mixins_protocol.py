from asyncio import Protocol

import redis.asyncio

from typing import TYPE_CHECKING

from app.core.redis_manager_v2.redis_client import RedisClient


class RedisCacheMixinsProtocol(Protocol):
    _prefix: str
    _client: redis.asyncio.Redis | RedisClient
    _key: str
    key: str
    client: redis.asyncio.Redis | RedisClient
    _decode_bytes: bool
