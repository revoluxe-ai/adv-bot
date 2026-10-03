from dependency_injector import containers, providers
from dependency_injector.providers import Provider, Container

from app.core.di.client_di.domain_managers_containers.analitycs_container import (
    AnalyticAndDataContainer,
)
from app.core.di.client_di.domain_managers_containers.products_container import (
    ProductsContainer,
)
from app.core.di.client_di.domain_managers_containers.promotion_container import (
    PromotionContainer,
)
from app.core.di.client_di.domain_managers_containers.reports_container import (
    ReportsContainer,
)
from app.core.mp.wb.api.auth_client_handler import AuthClientHandler

from app.core.mp.wb.api.domain_managers import (
    AnalyticsManager,
    ProductsManager,
    PromotionManager,
    ReportsManager,
)
from app.core.mp.wb.api.managers import WBDataManager, WBModifier


class WBDataContainer(containers.DeclarativeContainer):
    _auth_client_handler = providers.Dependency(instance_of=AuthClientHandler)
    _analytics_and_data_container: Container[AnalyticAndDataContainer] = (
        providers.Container(
            AnalyticAndDataContainer,
            _auth_client_handler=_auth_client_handler,
        )
    )

    _promotion_container: Container[PromotionContainer] = providers.Container(
        PromotionContainer,
        _auth_client_handler=_auth_client_handler,
    )

    _products_container: Container[ProductsContainer] = providers.Container(
        ProductsContainer,
        _auth_client_handler=_auth_client_handler,
    )

    _reports_container: Container[ReportsContainer] = providers.Container(
        ReportsContainer,
        _auth_client_handler=_auth_client_handler,
    )

    _analytics_domain_manager: Provider[AnalyticsManager] = (  # pyright: ignore
        _analytics_and_data_container.analytics_domain_manager
    )  # pyright: ignore

    _promotion_domain_manager: Provider[PromotionManager] = (  # pyright: ignore
        _promotion_container.promotion_domain_manager
    )  # pyright: ignore

    _products_domain_manager: Provider[ProductsManager] = (  # pyright: ignore
        _products_container.products_domain_manager
    )  # pyright: ignore

    _reports_domain_manager: Provider[ReportsManager] = (  # pyright: ignore
        _reports_container.reports_domain_manager
    )  # pyright: ignore

    wb_data_manager = providers.Singleton(
        WBDataManager,
        analytics_manager=_analytics_domain_manager,
        promotion_manager=_promotion_domain_manager,
        products_manager=_products_domain_manager,
        reports_manager=_reports_domain_manager,
    )

    wb_promotion_manager = providers.Singleton(
        WBModifier,
        promotion_manager=_promotion_domain_manager,
    )
