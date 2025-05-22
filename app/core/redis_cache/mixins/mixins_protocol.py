from asyncio import Protocol

import redis.asyncio


class RedisCacheMixinsProtocol(Protocol):
    _prefix: str
    _client: redis.asyncio.Redis
    _key: str
