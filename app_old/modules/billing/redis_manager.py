from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager
from app.core.redis_manager_v2.mixins.billing_check import BillingCheckMixin


class RedisManager(BillingCheckMixin, BaseRedisManager):
    pass
