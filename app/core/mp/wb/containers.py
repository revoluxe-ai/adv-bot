# app/core/mp/wb/containers.py
from __future__ import annotations

import httpx
from dependency_injector import containers, providers

from .adapters.promotion_v1_adapter import PromotionV1Adapter
from .base_wb_api_manager import BaseWBApiManager
from .factories.adapter_factory import WbApiAdapterFactory
from .promotion_manager import PromotionManager
from .rate_limit.storage import RateLimitStorage
from .services.promotion_bids_service import PromotionBidsService
from .tokens.token_manager import TokenManagerFactory


class WBApiContainer(containers.DeclarativeContainer):
    """Dependency injection container for WB API components."""

    config = providers.Configuration()

    # Singleton HTTP клиент с настройкой base_url из конфигурации
    http_client = providers.Singleton(
        httpx.AsyncClient,
        base_url=config.promotion.base_url,
        timeout=30.0,
        headers={"User-Agent": "WB-Bot/1.0"},
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
    )

    # Singleton для хранилища лимитов запросов (Rate Limiting)
    rate_limit_storage = providers.Singleton(RateLimitStorage)

    # Singleton фабрика для менеджеров токенов
    token_manager_factory = providers.Singleton(TokenManagerFactory)

    # Singleton фабрика адаптеров WB API
    wb_api_adapter_factory = providers.Singleton(WbApiAdapterFactory)

    # PromotionManager with injected adapter factory
    promotion_manager = providers.Factory(
        PromotionManager,
        adapter_factory=wb_api_adapter_factory,
    )

    # PromotionBidsService as Singleton using PromotionManager
    promotion_bids_service = providers.Singleton(
        PromotionBidsService,
        promotion_manager=promotion_manager,
    )

    # Singleton адаптеры для каждой версии
    promotion_adapter_v1 = providers.Singleton(
        PromotionV1Adapter,
        http_client=http_client,  # ← инжекция HTTP клиента
        wb_access=providers.Dependency(),  # Передается при создании
    )

    # Фабрика для создания BaseWBApi с нужными адаптерами
    wb_api_factory = providers.Factory(
        BaseWBApiManager,
        wb_access=providers.Dependency(),
        http_client=http_client,
    )
