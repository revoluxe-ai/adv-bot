from app.core.redis_cache import RedisCacheBase
from app.core.redis_cache.mixins.data_types.pass_time_redis_cache_base import (
    PassTimeRedisCacheBase,
)
from ..redis_cache_wrapper import RedisCacheAdvSettingsWrapper as AdvSettingRedisCache


class LastTargetPlaceUpV2(  # pyright: ignore[reportIncompatibleVariableOverride]
    AdvSettingRedisCache,
    RedisCacheBase,
    PassTimeRedisCacheBase,
    prefix="last_set_up_target_place",
):
    pass


class LastTargetPlaceDownV2(  # pyright: ignore[reportIncompatibleVariableOverride]
    AdvSettingRedisCache,
    RedisCacheBase,
    PassTimeRedisCacheBase,
    prefix="last_set_down_target_place",
):
    pass
