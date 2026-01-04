"""Контейнер для DI-зависимостей приложения."""

__all__ = ("AppContainer",)

from dependency_injector import containers, providers
from redis.asyncio import Redis

from app.core.redis_manager_v2.redis_client import RedisClient
from . import databases
from .module_resources import ModuleResources
from app.configs.app_config import AppConfig  # Добавляем импорт AppConfig здесь

def create_redis_client(redis_config: AppConfig) -> Redis:  # pyright: ignore
    redis: Redis = databases.create_redis_client(redis_config)  # pyright: ignore
    return redis  # pyright: ignore


class AppContainer(containers.DeclarativeContainer):
    """Главный DI-контейнер приложения. Содержит все основные сервисы и конфигурации."""

    # TODO: Варить надо те контейенры, которые инжектим
    wiring_config = containers.WiringConfiguration(
        packages=[
            "app.core.redis_manager_v2",
            "app.modules.wb_adv_updater.get_text_to_predict_ctr_dict",
            "app.modules.common_slaves.wildberries.super_cabinet_manager",
            "app.modules.shop_runner.bidder.bidder_func",
            "app.modules.wb_adv_updater.min_ctr_manager.min_ctr_manager",
            "app.client_bot",  # client_bot utils используют data_manager
            "app.modules.shop_menu",  # ShopMenu использует DI для redis_client_wrapper
            "app.modules.wb_adv_updater",  # wb_adv_updater использует min_ctr_manager
            "app.core.redis_cache",
            "app.modules.shop_runner.run_process_func",
            "app.core.mp.wb.wb_base_manager",
            "app.modules.wb_adv_updater.calculated_keywords_manager.calculated_keywords_manager"

        ]
    )

    # TODO: Нужен еще тест, который проверяет не забыл ли я что приварить

    settings = providers.Singleton(AppConfig.create)
    redis_client = providers.Singleton(  # pyright: ignore
        create_redis_client,  # pyright: ignore
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

    _redis_lifecycle: providers.Resource[Redis] = providers.Resource(  # pyright: ignore
        databases.RedisLifecycle,
        client=redis_client,
    )
