from typing import Optional

from app.core.redis_cache import RedisCacheBase
from app.core.redis_cache.mixins.main_objects_mixins.wb_shop_redis_cache import (
    WBShopRedisCache,
)
from . import Error
from ..full_redis_key import FullRedisKey


class ErrorHandler(
    RedisCacheBase, FullRedisKey, WBShopRedisCache, prefix="WBShopStatusHandler"
):
    @property
    def _unique_id(self) -> str:
        return self.key + ":" + "error_handler"

    async def set(self, func_name: str, error: Error) -> None:
        full_key = self.get_full_key(func_name)
        json_data = error.to_json()
        await self.client.set(full_key, json_data)

    async def get(self, func_name: str) -> Optional[Error]:
        full_key = self.get_full_key(func_name)
        value = await self.client.get(full_key)
        if not value:
            return None
        result = value.decode()
        error = Error.from_json(result)
        return error
