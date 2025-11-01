__all__ = ("RateLimitMixin",)


import math
from typing import TYPE_CHECKING

from ..base_redis_manager_protocol import BaseRedisManagerProtocol

if TYPE_CHECKING:  # pragma: no cover - hints only
    from typing import Tuple


class RateLimitMixin:
    rate_limit_prefix = "wb_rate_limit"

    def _make_rate_limit_key(self, ip: str) -> str:
        try:
            # type: ignore[call-arg]
            return self._get_key(ip)  # pragma: no cover - delegated to BaseRedisManager
        except AttributeError:
            return f"{self.rate_limit_prefix}:{ip}"

    async def is_ip_blocked(
        self: BaseRedisManagerProtocol, ip: str
    ) -> tuple[bool, float]:
        key = self._make_rate_limit_key(ip)
        ttl_ms = await self._client.pttl(key)
        if ttl_ms == -2:
            return False, 0.0
        if ttl_ms <= 0:
            # key exists without ttl or error – treat as minimal wait
            return True, 1.0
        return True, ttl_ms / 1000

    async def block_ip(
        self: BaseRedisManagerProtocol, ip: str, ttl_seconds: float
    ) -> None:
        ttl_ms = max(int(math.ceil(ttl_seconds * 1000)), 1)
        key = self._make_rate_limit_key(ip)
        await self._client.set(key, "1", px=ttl_ms)

    async def delete_block(self: BaseRedisManagerProtocol, ip: str) -> None:
        key = self._make_rate_limit_key(ip)
        await self._client.delete(key)

    async def refresh_block(
        self: BaseRedisManagerProtocol, ip: str, ttl_seconds: float
    ) -> None:
        ttl_ms = max(int(math.ceil(ttl_seconds * 1000)), 1)
        key = self._make_rate_limit_key(ip)
        refreshed = await self._client.pexpire(key, ttl_ms)
        if not refreshed:
            await self._client.set(key, "1", px=ttl_ms)

