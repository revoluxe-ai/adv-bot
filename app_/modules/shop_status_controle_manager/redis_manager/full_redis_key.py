from app.core.redis_cache.mixins.mixins_protocol import RedisCacheMixinsProtocol


class FullRedisKey(RedisCacheMixinsProtocol):
    def get_full_key(self, func_name: str) -> str:
        base_key = self._get_unique_id()
        full_key = f"{base_key}:{func_name}"
        return full_key
