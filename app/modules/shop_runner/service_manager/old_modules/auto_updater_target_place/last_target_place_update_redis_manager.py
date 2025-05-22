from app.core.redis_cache.mixins.data_types.pass_time_redis_cache_base import (
    PassTimeRedisCacheBase,
)
from app.core.redis_cache.mixins.main_objects_mixins.adv_setting_redis_cache import (
    AdvSettingRedisCache,
)
from app.core.redis_cache.redis_cache_base import RedisCacheBase


class LastTargetPlaceUpdateRedisManager(
    AdvSettingRedisCache,
    RedisCacheBase,
    PassTimeRedisCacheBase,
    prefix="last_target_place_update",
):
    pass
