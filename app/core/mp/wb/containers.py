# app/core/mp/wb/containers.py
from __future__ import annotations

import httpx
from dependency_injector import containers, providers

from .rate_limit.storage import RateLimitStorage
from .tokens.token_manager import TokenManagerFactory
from .factories.adapter_factory import WbApiAdapterFactory


class WBApiContainer(containers.DeclarativeContainer):
    """DI контейнер WB API по ТЗ."""

    config = providers.Configuration()

    # Один AsyncClient на раздел API (сейчас только promotion)
    promotion_http_client = providers.Singleton(
        httpx.AsyncClient,
        base_url=config.promotion.base_url,   # пример: "https://advert-api.wildberries.ru/"
        timeout=30.0,
    )

    # Централизованное хранилище RL
    rate_limit_storage = providers.Singleton(RateLimitStorage)

    # Фабрика токен-менеджеров (per shop_id)
    token_manager_factory = providers.Singleton(TokenManagerFactory)

    # Фабрика адаптеров с кэшом по (shop_id, section, version)
    adapter_factory = providers.Singleton(
        WbApiAdapterFactory,
        promotion_http_client=promotion_http_client,
        token_manager_factory=token_manager_factory,
        rate_limit_storage=rate_limit_storage,  # передадим для декоратора/адаптера
    )