from app.core.redis_manager_v2.base_protocol import BaseRedisManagerProtocol
from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager
from app.core.redis_manager_v2.mixins.billing_check import BillingCheckMixin


class RedisManager(BillingCheckMixin, BaseRedisManagerProtocol):
    """Менеджер для проверки биллинга в Redis с поддержкой TTL и префикса."""
    pass