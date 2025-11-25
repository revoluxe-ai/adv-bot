import datetime

from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword


class LastKeywordStampTimestampCache(BaseRedisManager):
    prefix = 'last_keyword_stamp_timestamp_cache'
    def _get_key(self, keyword: CalculatedKeyword) -> str:
        return self.prefix + ':' + str(keyword.keyword_setting_original_id)

    async def get(self, keyword: CalculatedKeyword) -> datetime.datetime | None:
        key = self._get_key(keyword)
        value = await self._client.get(key)
        if value is None:
            return None
        value_dt = datetime.datetime.fromisoformat(value)
        return value_dt


    async def set(self, keyword: CalculatedKeyword) -> None:
        key = self._get_key(keyword)
        value: datetime.datetime | None = keyword.position_update
        if value is None:
            return None
        value_str = value.astimezone(datetime.timezone.utc).isoformat()
        _ = await self._client.set(key, value_str)
        return None