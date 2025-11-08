import datetime
from abc import ABC

from app.core.redis_cache.mixins.mixins_protocol import RedisCacheMixinsProtocol


class SimpleTimeStamp(ABC, RedisCacheMixinsProtocol):
    async def set_timestamp(self) -> None:
        now = datetime.datetime.now()
        value = now.isoformat()
        await self._client.set(self._key, value)

    async def get(self) -> datetime.datetime | None:
        value_bytes: bytes | str | None = await self._client.get(self._key)
        if not value_bytes:
            return None
        if isinstance(value_bytes, bytes):
            value = value_bytes.decode()
        else:
            value = value_bytes
        timestamp = datetime.datetime.fromisoformat(value)
        return timestamp
