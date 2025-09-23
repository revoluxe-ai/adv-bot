from app.core.redis_manager.base_redis_manager import BaseRedisProtocol
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import AdvSetting


class AdvBaseRedis(BaseRedisProtocol):
    def __init__(self, adv: AdvSetting):
        self._adv = adv

    @property
    def _key(self) -> str:
        unique_id = self._adv.adv_id
        return f"{self.prefix}:{unique_id}"


class KeywordBaseRedis(BaseRedisProtocol):
    def __init__(self, calculated_keyword: CalculatedKeyword):
        self._kw = calculated_keyword

    @property
    def _key(self) -> str:
        return f"{self.prefix}:{self._kw.keyword_setting_original_id}"
