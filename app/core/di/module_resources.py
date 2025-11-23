"""
Агрегатор модульных DI-контейнеров.
"""

from dependency_injector import containers, providers

from app.core.mp.wb.di import WBManagerHubFactoryContainer
from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.billing.di import BillingContainer
from app.modules.shop_runner.modules.max_auto_bid_manager.di import AutoMaxCpmContainer
from app.modules.shop_runner.service_manager.services.predict_ctr_update_manager.di import (
    PredictCTRManagerContainer,
)



class ModuleResources(containers.DeclarativeContainer):
    """Содержит DI-контейнеры всех модулей приложения."""

    redis_client_wrapper: providers.Dependency[RedisClient] = providers.Dependency(
        instance_of=RedisClient
    )

    billing = providers.Container(
        BillingContainer,
        redis_client_wrapper=redis_client_wrapper,
    )

    predict_ctr_manager: providers.Container[PredictCTRManagerContainer] = (
        providers.Container(
            PredictCTRManagerContainer,
            redis_client_wrapper=redis_client_wrapper,
        )
    )

    auto_max_cpm_manager = providers.Container(
        AutoMaxCpmContainer,
        redis_client_wrapper=redis_client_wrapper,
    )

    wb_manager_hub_factory_container = providers.Container(WBManagerHubFactoryContainer)

    # Пример для будущих модулей:
    # analytics = providers.Container(AnalyticsContainer, redis_client_wrapper=redis_client_wrapper)
