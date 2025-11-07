
# TODO: Выключил тут Pycharm inspection для чтобы быстрее выкатить в прод, надо будет переделать потом

from __future__ import annotations

import math
from typing import TYPE_CHECKING, TypeAlias


if TYPE_CHECKING:
    from ..base_redis_manager import BaseRedisManager


    class _RateLimitProto(BaseRedisManager): # type: ignore[misc] # BaseRedisManager is ABC, cannot be directly instantiated
        rate_limit_prefix: str
        async def _reset_success_counter(self, ip: str) -> None: ...
        async def _reset_error_counter(self, ip: str) -> None: ...
        def _ts_key(self, ip: str) -> str: ...
        def _get_key(self, ip: str) -> str: ... # Add _get_key to the protocol

    # Use TypeAlias for better readability and to combine types for self
    _SelfType: TypeAlias = BaseRedisManager | _RateLimitProto

else:
    _SelfType = "BaseRedisManager"


class RateLimitMixin:
    rate_limit_prefix = "wb_rate_limit"

    def _get_key(self: _SelfType, ip: str) -> str:
        return f"{self.rate_limit_prefix}:{ip}"

    async def is_ip_blocked(
        self: _SelfType, ip: str
    ) -> tuple[bool, float]:
        key = self._get_key(ip)
        ttl_ms = await self._client.pttl(key)
        if ttl_ms == -2:
            return False, 0.0
        if ttl_ms <= 0:
            # key exists without ttl or error – treat as minimal wait
            return True, 1.0
        return True, ttl_ms / 1000

    async def block_ip(
        self: _SelfType, ip: str, ttl_seconds: float
    ) -> None:
        ttl_ms = max(int(math.ceil(ttl_seconds * 1000)), 1)
        key = self._get_key(ip)
        await self._client.set(key, "1", px=ttl_ms)

    async def delete_block(self: _SelfType, ip: str) -> None:
        key = self._get_key(ip)
        await self._client.delete(key)

    async def refresh_block(
        self: _SelfType, ip: str, ttl_seconds: float
    ) -> None:
        ttl_ms = max(int(math.ceil(ttl_seconds * 1000)), 1)
        key = self._get_key(ip)
        refreshed = await self._client.pexpire(key, ttl_ms)
        if not refreshed:
            await self._client.set(key, "1", px=ttl_ms)

    async def increment_success_counter(
        self: _SelfType, ip: str
    ) -> int:
        """Увеличить счётчик последовательных успехов, вернуть новое значение."""
        key = f"{self.rate_limit_prefix}:success:{ip}"
        # Use Lua script for atomic incr + expire
        lua_script = """
        local count = redis.call('INCR', KEYS[1])
        redis.call('EXPIRE', KEYS[1], ARGV[1])
        return count
        """
        count = await self._client.eval(lua_script, 1, key, 3600)
        # Сбрасываем счётчик ошибок
        await self._reset_error_counter(ip)
        return int(count)

    async def increment_error_counter(
        self: _SelfType, ip: str
    ) -> int:
        """Увеличить счётчик последовательных ошибок, вернуть новое значение."""
        key = f"{self.rate_limit_prefix}:errors:{ip}"
        # Use Lua script for atomic incr + expire
        lua_script = """
        local count = redis.call('INCR', KEYS[1])
        redis.call('EXPIRE', KEYS[1], ARGV[1])
        return count
        """
        count = await self._client.eval(lua_script, 1, key, 3600)
        # Сбрасываем счётчик успехов
        await self._reset_success_counter(ip)
        return int(count)

    async def _reset_success_counter(self: _SelfType, ip: str) -> None:
        """Сбросить счётчик последовательных успехов."""
        key = f"{self.rate_limit_prefix}:success:{ip}"
        await self._client.delete(key)

    async def _reset_error_counter(self: _SelfType, ip: str) -> None:
        """Сбросить счётчик последовательных ошибок."""
        key = f"{self.rate_limit_prefix}:errors:{ip}"
        await self._client.delete(key)

    # --- Метки времени последнего 429 ---
    def _ts_key(self, ip: str) -> str:
        return f"{self.rate_limit_prefix}:last_err_ts:{ip}"

    async def set_last_error_ts(self: _SelfType, ip: str) -> None:
        from time import time as _time
        await self._client.set(self._ts_key(ip), str(int(_time())), ex=3600)

    async def get_last_error_ts(self: _SelfType, ip: str) -> float:
        value = await self._client.get(self._ts_key(ip))
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

