import datetime

from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword


class LastKeywordStampTimestampCache(BaseRedisManager):
    prefix = 'last_keyword_stamp_timestamp_cache'
    def _get_key(self, keyword: CalculatedKeyword) -> str:
        return self.prefix + ':' + str(keyword.keyword_setting_original_id)

    async def get(self, keyword: CalculatedKeyword):
        key = self._get_key(keyword)
        value_bytes: bytes | str | None = await self._client.get(key)
        if value_bytes is None:
            return None
        value = value_bytes.decode()
        value_dt = datetime.datetime.strptime(value, self.__strftime)
        return value_dt


    async def set(self, keyword: CalculatedKeyword) -> None:
        key = self._get_key(keyword)
        value: datetime.datetime | None = keyword.position_update
        if value is None:
            return None
        value_str = value.strftime(self.__strftime)
        await self._client.set(key, value_str)
        return None

    @property
    def __strftime(self) -> str:
        return '%Y-%m-%d %H:%M:%S'