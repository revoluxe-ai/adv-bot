
from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword


class RedisLastTotalViews(BaseRedisManager):

    prefix = "last_views_on_bidder"

    def _get_key(self, keyword: CalculatedKeyword) -> str:
        return self.prefix + ":" + str(keyword.keyword_setting_original_id)

    async def get(self, keyword: CalculatedKeyword) -> int | None:
        key = self._get_key(keyword)
        value: str | bytes | None = await self._client.get(key)
        if value is None:
            return None
        if isinstance(value, bytes):  # pyright: ignore
            value = value.decode()
        return int(value)

    async def set(self, keyword: CalculatedKeyword) -> None:
        key = self._get_key(keyword)
        views: int = keyword.total_views
        if views:
            views_str: str = str(views)
            await self._client.set(key, views_str)
