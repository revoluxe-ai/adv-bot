"""Redis-кэширование для управления экспонентой."""
from app.core.redis_cache import  RedisCacheBase
from app.core.redis_cache.mixins.data_types.pass_time_redis_cache_base import PassTimeRedisCacheBase
from ..redis_cache_wrapper import RedisCacheAdvSettingsWrapper as AdvSettingRedisCache


PASS_TIME = 15 * 60  # 15 минут между изменениями


class LastExponentRaiseV2( # pyright: ignore[reportIncompatibleVariableOverride]
    AdvSettingRedisCache,
    RedisCacheBase,
    PassTimeRedisCacheBase,
    prefix="LastExponentRaiseV2",
):
    pass


class LastExponentDownV2( # pyright: ignore[reportIncompatibleVariableOverride]
    AdvSettingRedisCache,
    RedisCacheBase,
    PassTimeRedisCacheBase,
    prefix="LastExponentDownV2",
):
    pass
