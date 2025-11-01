"""Redis-кэширование для управления белым списком."""

from app.core.redis_cache.mixins.data_types.pass_time_redis_cache_base import (
    PassTimeRedisCacheBase,
)
from app.core.redis_cache.mixins.main_objects_mixins.adv_setting_redis_cache import (
    AdvSettingRedisCache,
)
from app.core.redis_cache.redis_cache_base import RedisCacheBase


class LastAutoAddPhraseToWhiteListV2(
    AdvSettingRedisCache,
    RedisCacheBase,
    PassTimeRedisCacheBase,
    prefix="LastAutoAddPhraseToWhiteListV2",
):
    """Redis-кэш для отслеживания времени последнего добавления фразы в белый список."""

    pass


class LastAutoDeleteFromWhiteListV2(
    AdvSettingRedisCache,
    RedisCacheBase,
    PassTimeRedisCacheBase,
    prefix="LastAutoDeleteFromWhiteListV2",
):
    """Redis-кэш для отслеживания времени последнего удаления фразы из белого списка."""

    pass
