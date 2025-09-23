"""DI контейнер для WB API компонентов."""

import httpx
from dependency_injector import containers, providers

from .adapters.promotion.v1_adapter import PromotionV1Adapter
from .base_wb_api import BaseWBApi


class WBApiContainer(containers.DeclarativeContainer):
    """DI контейнер для WB API компонентов."""

    config = providers.Configuration()

    # Singleton HTTP клиент - один на все приложение
    http_client = providers.Singleton(
        httpx.AsyncClient,
        timeout=httpx.Timeout(30.0),
        headers={"User-Agent": "WB-Bot/1.0"},
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
    )

    # Singleton адаптеры для каждой версии
    promotion_adapter_v1 = providers.Singleton(
        PromotionV1Adapter,
        http_client=http_client,  # ← инжекция HTTP клиента
        wb_access=providers.Dependency(),  # Передается при создании
    )

    # Фабрика для создания BaseWBApi с нужными адаптерами
    wb_api_factory = providers.Factory(
        lambda wb_access, http_client: BaseWBApi(
            wb_access=wb_access,
            http_client=http_client,  # Для совместимости, но адаптеры уже получили свой
            domain_versions=WBApiVersionConfig.get_versions(),
        ),
        wb_access=providers.Dependency(),
        http_client=http_client,
    )
