"""Контейнер для DI-зависимостей приложения."""

__all__ = ("AppContainer",)

from dependency_injector import containers, providers
from dependency_injector.resources import AsyncResource
from redis.asyncio import Redis

from app.core.redis_manager_v2.redis_client import RedisClient
from . import databases
from .module_resources import ModuleResources
from ...configs import AppConfig


def create_redis_client(redis_config: AppConfig) -> Redis:
    redis = databases.create_redis_client(redis_config)
    return redis


class AppContainer(containers.DeclarativeContainer):
    """Главный DI-контейнер приложения. Содержит все основные сервисы и конфигурации."""
    wiring_config = containers.WiringConfiguration(
        packages=[
            "app.core.redis_manager_v2",
            "app.modules.wb_adv_updater.get_text_to_predict_ctr_dict",
            "app.modules.common_slaves.wildberries.super_cabinet_manager",
        ]
    )

    settings = providers.Singleton(AppConfig.create)
    redis_client = providers.Singleton(
        create_redis_client,
        redis_config=settings,
    )
    # Обёртка над raw Redis, предоставляющая унифицированный API
    redis_client_wrapper = providers.Singleton(
        RedisClient,
        redis_client=redis_client,
    )

    module_resources: providers.Container[ModuleResources] = providers.Container(
        ModuleResources,
        redis_client_wrapper=redis_client_wrapper,
    )

    _redis_lifecycle: providers.Resource[AsyncResource[Redis]] = providers.Resource(
        databases.RedisLifecycle,
        client=redis_client,
    )
