"""Под-контейнер DI для модуля billing.

Отделяет тонкие менеджеры (RedisManager / RedisLock) от корневого контейнера.
Корневой контейнер (AppContainer) пробрасывает общий redis_client_wrapper как зависимость.

Преимущества:
- Локализация зависимостей модуля
- Возможность расширить модуль (добавить новые менеджеры) без изменения root контейнера
- Тесты могут подменять BillingContainer целиком или отдельные провайдеры
"""
from __future__ import annotations

from dependency_injector import containers, providers

from app.core.redis_manager_v2.redis_client import RedisClient
from .redis_lock import RedisLock
from .redis_manager import RedisManager


class BillingContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "app.modules.billing.billing",  # функции/корутины модуля billing
        ]
    )

    # Зависимость: обёрнутый RedisClient из корневого контейнера
    redis_client_wrapper = providers.Dependency(instance_of=RedisClient)

    # Тонкие менеджеры
    redis_manager = providers.Singleton(
        RedisManager,
        redis_client=redis_client_wrapper,
    )
    redis_lock = providers.Singleton(
        RedisLock,
        redis_client=redis_client_wrapper,
    )


__all__ = ["BillingContainer"]
