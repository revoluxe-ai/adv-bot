from app.core.redis_cache import AdvSettingRedisCache
from app.modules.common_slaves.wildberries.models import AdvSetting


class RedisCacheAdvSettingsWrapper(AdvSettingRedisCache):
    def __init__(self, adv_setting: AdvSetting,) -> None:
        super().__init__(adv_setting)