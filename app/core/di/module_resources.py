"""
Агрегатор модульных DI-контейнеров.
"""

import typing

from dependency_injector import containers, providers

from app.modules.billing.di import BillingContainer

if typing.TYPE_CHECKING:
    pass


class ModuleResources(containers.DeclarativeContainer):
    """Содержит DI-контейнеры всех модулей приложения."""
    redis_client_wrapper: providers.Dependency[typing.Never] = providers.Dependency()

    billing = providers.Container(
        BillingContainer,
        redis_client_wrapper=redis_client_wrapper,
    )

    # Пример для будущих модулей:
    # analytics = providers.Container(AnalyticsContainer, redis_client_wrapper=redis_client_wrapper)
