from app.core.redis_cache import RedisCacheBase
from app.core.redis_cache.mixins.main_objects_mixins.wb_shop_redis_cache import (
    WBShopRedisCache,
)
from . import Success
from ..full_redis_key import FullRedisKey


class SuccessHandler(
    WBShopRedisCache, RedisCacheBase, FullRedisKey, prefix="WBShopSuccessHandler"
):
    def _get_unique_id(self) -> str:
        key = self.key
        return key + ":" + "SuccessHandler"

    async def set(self, func_name: str, success: Success) -> None:
        full_key = self.get_full_key(func_name)
        json_data = success.to_json()
        await self.client.set(full_key, json_data)

    async def get(self, func_name: str) -> Success | None:
        full_key = self.get_full_key(func_name)
        value = await self.client.get(full_key)
        if not value:
            return None
        data = value.decode()
        success = Success.from_json(data)
        return success
