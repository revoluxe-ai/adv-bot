from app.core.redis_cache import AdvSettingRedisCache, RedisCacheBase, SimpleTimeStamp


class LastUpdateFirstPhrase(
    AdvSettingRedisCache,
    RedisCacheBase,
    SimpleTimeStamp,
    prefix="LastUpdateFirstPhrase",
):
    pass
