from collections.abc import Awaitable

import redis

from app.core.redis_manager.base_redis_manager import BaseRedis
from app.settings import settings


class RedisShopManager(BaseRedis):
    _active_shops_set_name = "active_shops"
    _shops_heartbeat_prefix = "shops_heartbeat:"

    # Упрощенный скрипт (TTL жестко задан в скрипте)
    _GET_FREE_SHOP_SCRIPT = """
        local shops = redis.call('SMEMBERS', KEYS[1])
        for _, shop_id in ipairs(shops) do
            local lock_key = ARGV[1]..shop_id
            local ttl = tonumber(ARGV[2])
            if redis.call('SET', lock_key, '1', 'EX', ttl, 'NX') then
                return shop_id
            end
        end
        return nil
        """

    def __init__(self) -> None:
        super().__init__()
        self._script_sha = None
        self.DEFAULT_TTL = settings.SHOPS_WORKS_TLL

    async def initialize_lua_script(self) -> None:
        """Загрузка скрипта при инициализации"""
        self._script_sha = await self._client.script_load(self._GET_FREE_SHOP_SCRIPT)

    async def update_active_shops(self, shop_ids: list[str]) -> None:
        """Добавляет магазины в множество активных"""
        await self._client.sadd(self._active_shops_set_name, *shop_ids)

    async def renew_shop_ttl(self, shop_id: str) -> None:
        """Обновляет TTL для магазина"""
        ttl = self.DEFAULT_TTL
        key = f"{self._shops_heartbeat_prefix}{shop_id}"
        await self._client.setex(key, ttl, "1")

    async def get_next_free_shop_id(self) -> str | None:
        if not self._script_sha:
            await self.initialize_lua_script()
        ttl_seconds = self.DEFAULT_TTL
        try:
            result: Awaitable[bytes | None] = self._client.evalsha(
                self._script_sha,
                1,
                self._active_shops_set_name,  # KEYS[1]
                self._shops_heartbeat_prefix,  # ARGV[1]
                str(ttl_seconds),  # ARGV[2]
            )

            shop_id = await result
            if not shop_id:
                return None
            shop_id = shop_id.decode()
            return str(shop_id)
        except redis.exceptions.NoScriptError:
            await self.initialize_lua_script()
            return await self.get_next_free_shop_id()

    async def remove_shops(self, shop_ids: list[str]) -> None:
        """Удаляет магазины из множества активных и удаляет их heartbeat-ключи"""
        if not shop_ids:
            return

        # Удалить из множества
        await self._client.srem(self._active_shops_set_name, *shop_ids)

        # Удалить heartbeat-ключи
        heartbeat_keys = [f"{self._shops_heartbeat_prefix}{shop_id}" for shop_id in shop_ids]
        if heartbeat_keys:
            await self._client.delete(*heartbeat_keys)
