"""Redis-кэширование для управления экспонентой."""

from app.core.redis_cache.mixins.data_types.pass_time_redis_cache_base import (
    PassTimeRedisCacheBase,
)
from app.core.redis_cache.mixins.main_objects_mixins.adv_setting_redis_cache import (
    AdvSettingRedisCache,
)
from app.core.redis_cache.redis_cache_base import RedisCacheBase


class LastExponentRaiseV2(
    AdvSettingRedisCache,
    RedisCacheBase,
    PassTimeRedisCacheBase,
    prefix="LastExponentRaiseV2",
):
    """Redis-кэш для отслеживания времени последнего повышения экспоненты."""

    pass


class LastExponentDownV2(
    AdvSettingRedisCache,
    RedisCacheBase,
    PassTimeRedisCacheBase,
    prefix="LastExponentDownV2",
):
    """Redis-кэш для отслеживания времени последнего понижения экспоненты."""

    pass
