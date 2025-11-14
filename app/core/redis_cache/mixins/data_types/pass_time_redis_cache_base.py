import datetime
from abc import ABC

from ..mixins_protocol import RedisCacheMixinsProtocol


class PassTimeRedisCacheBase(ABC, RedisCacheMixinsProtocol):
    async def check_pass_time(self, pass_time_sec: int) -> bool:
        timestamp = await self.get()
        if not timestamp:
            return True
        now = datetime.datetime.now()
        if timestamp + datetime.timedelta(seconds=pass_time_sec) <= now:
            return True
        else:
            return False

    async def set(self) -> None:
        now = datetime.datetime.now()
        timestamp = now.isoformat()
        await self.client.set(self._key, timestamp)

    async def get(self) -> datetime.datetime | None:
        value_bytes = await self.client.get(self._key)
        if not value_bytes:
            return None
        if isinstance(value_bytes, bytes):
            value = value_bytes.decode()
        else:
            value = value_bytes
        timestamp = datetime.datetime.fromisoformat(value)
        return timestamp
