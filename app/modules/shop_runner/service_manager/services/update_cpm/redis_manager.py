from app.core.redis_manager_v2 import mixins, BaseRedisManager


class RedisManager(mixins.WBPositionsMixin, BaseRedisManager):
    pass
