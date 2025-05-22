from app.core.redis_cache import AdvSettingRedisCache, SimpleTimeStamp, RedisCacheBase


class LastUpdateFirstPhrase(
    AdvSettingRedisCache,
    RedisCacheBase,
    SimpleTimeStamp,
    prefix="LastUpdateFirstPhrase",
):
    pass
