"""RedisLockManager — менеджер для управления блокировками биллинга в Redis.

Теперь вся логика (формирование ключей, acquire/release/is_locked/extend и guard)
перенесена в BillingLockMixin. Этот класс — тонкая обёртка для удобного использования
через DI (наследует BaseRedisManager и миксин).
"""

from __future__ import annotations

from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager
from app.core.redis_manager_v2.mixins.billing_lock import BillingLockMixin


class RedisLock(BillingLockMixin, BaseRedisManager):
    """Тонкий класс блокировок биллинга с поддержкой TTL и префикса.

    Вся функциональность реализована в BillingLockMixin.
    Порядок наследования важен: миксин идёт первым, чтобы его _get_key
    закрыл абстрактный метод BaseRedisManager.
    """

    prefix = "billing_lock"
    default_ttl = 600  # 1 минута по умолчанию

    # Дополнительная логика при необходимости может быть добавлена здесь.
    pass
