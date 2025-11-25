"""Redis-кэширование для управления белым списком."""

from app.core.redis_cache import RedisCacheBase
from app.core.redis_cache.mixins.data_types.pass_time_redis_cache_base import (
    PassTimeRedisCacheBase,
)


from ..redis_cache_wrapper import RedisCacheAdvSettingsWrapper as AdvSettingRedisCache


class LastAutoAddPhraseToWhiteListV2(  # pyright: ignore[reportIncompatibleVariableOverride]
    AdvSettingRedisCache,
    RedisCacheBase,
    PassTimeRedisCacheBase,
    prefix="LastAutoAddPhraseToWhiteList",
):
    """Redis-кэш для отслеживания времени последнего добавления фразы в белый список."""

    pass


class LastAutoDeleteFromWhiteListV2(  # pyright: ignore[reportIncompatibleVariableOverride]
    AdvSettingRedisCache,
    RedisCacheBase,
    PassTimeRedisCacheBase,
    prefix="LastAutoDeleteFromWhiteList",
):
    """Redis-кэш для отслеживания времени последнего удаления фразы из белого списка."""

    pass
