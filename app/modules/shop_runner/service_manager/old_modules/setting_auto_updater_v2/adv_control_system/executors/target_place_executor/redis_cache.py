"""Redis-кэширование для управления целевой позицией."""

from app.core.redis_cache.mixins.data_types.pass_time_redis_cache_base import (
    PassTimeRedisCacheBase,
)
from app.core.redis_cache.mixins.main_objects_mixins.adv_setting_redis_cache import (
    AdvSettingRedisCache,
)
from app.core.redis_cache.redis_cache_base import RedisCacheBase


class LastTargetPlaceUpV2(
    AdvSettingRedisCache,
    RedisCacheBase,
    PassTimeRedisCacheBase,
    prefix="LastTargetPlaceUpV2",
):
    """Redis-кэш для отслеживания времени последнего повышения ЦП (уменьшение номера)."""

    pass


class LastTargetPlaceDownV2(
    AdvSettingRedisCache,
    RedisCacheBase,
    PassTimeRedisCacheBase,
    prefix="LastTargetPlaceDownV2",
):
    """Redis-кэш для отслеживания времени последнего понижения ЦП (увеличение номера)."""

    pass
