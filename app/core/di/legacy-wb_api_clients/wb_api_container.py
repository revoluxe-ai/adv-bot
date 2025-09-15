"""Главный DI-контейнер для WB API доменов и версий."""

from app.core.mp.wb.api_client.promotion.generated.v1.marketing_i_prodvizhenie.client import (
    Client as PromotionV1Client,
)
from dependency_injector import containers, providers


def _build_shop_token_manager_factory():
    from app.core.mp.wb.token_management.factory import ShopTokenManagerFactory

    return ShopTokenManagerFactory()


def _build_enhanced_shop_token_manager_factory():
    from app.core.mp.wb.token_management.enhanced_factory import (
        EnhancedShopTokenManagerFactory,
    )

    return EnhancedShopTokenManagerFactory()


class PromotionV1ClientContainer(containers.DeclarativeContainer):
    """Контейнер для клиента Promotion API v1."""

    settings = providers.Dependency()

    client = providers.Singleton(
        PromotionV1Client,
        base_url=settings.provided.infrastructure.wb.api_url,
        timeout=settings.provided.infrastructure.wb.timeout,
    )


class PromotionClientContainer(containers.DeclarativeContainer):
    """Контейнер клиентов домена Promotion с версиями."""

    settings = providers.Dependency()

    v1 = providers.Container(
        PromotionV1ClientContainer,
        settings=settings,
    )


class PromotionV1Container(containers.DeclarativeContainer):
    """Контейнер версии v1 для домена Promotion."""

    client = providers.Dependency()
    wb_access = providers.Dependency()

    def _build_adapter(client, wb_access):
        from app.core.mp.wb.adapters.promotion.v1_adapter import PromotionV1Adapter

        return PromotionV1Adapter(http_client=client, wb_access=wb_access)

    adapter = providers.Singleton(
        _build_adapter,
        client=client,
        wb_access=wb_access,
    )


class PromotionContainer(containers.DeclarativeContainer):
    """Контейнер домена Promotion с версионными под-контейнерами."""

    client = providers.Dependency()
    wb_access = providers.Dependency()

    v1 = providers.Container(
        PromotionV1Container,
        client=client,
        wb_access=wb_access,
    )

    adapter = providers.DelegatedCallable(lambda v1: v1.adapter(), v1=v1)


class WBApiDIContainer(containers.DeclarativeContainer):
    """Главный контейнер WB API, агрегирующий домены и версии."""

    wiring_config = containers.WiringConfiguration(packages=["app"])

    # Общие зависимости (Singleton HTTP client из AppContainer)
    http_client = providers.Dependency(
        instance_of=object, default=AppContainer.wb_api_httpx_session
    )
    wb_access = providers.Dependency(instance_of=object)

    # Фабрика менеджеров токенов (singleton)
    token_manager_factory = providers.Singleton(_build_shop_token_manager_factory)

    # Enhanced factory
    enhanced_token_manager_factory = providers.Singleton(
        _build_enhanced_shop_token_manager_factory
    )

    # Провайдер текущего менеджера токенов
    shop_token_manager = providers.Callable(
        lambda factory: factory.get_or_create(), factory=token_manager_factory
    )

    enhanced_shop_token_manager = providers.Callable(
        lambda factory: factory.get_or_create(), factory=enhanced_token_manager_factory
    )
